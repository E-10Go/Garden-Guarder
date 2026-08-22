from arduino.app_utils import *
import cv2
import onnxruntime as ort
import numpy as np
import time
import os
import threading
from flask import Flask, Response

# ==========================================
# 1. INITIALIZATION 
# ==========================================
print("[SYSTEM] Booting IP102 Live AI Detection (512x512 Mode)...")

current_folder = os.path.dirname(__file__)
model_path = os.path.join(current_folder, "best1.onnx")
session = ort.InferenceSession(model_path)
input_name = session.get_inputs()[0].name

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[ERROR] Cannot open camera")
    exit()

# Ensure snapshots folder exists
snapshots_dir = os.path.join(current_folder, "snapshots")
os.makedirs(snapshots_dir, exist_ok=True)

# Full IP102 Class Names Dictionary (Synchronized with your new YAML)
CLASS_NAMES = {
    0: 'rice leaf roller', 1: 'rice leaf caterpillar', 2: 'paddy stem maggot', 3: 'asiatic rice borer', 4: 'yellow rice borer',
    5: 'rice gall midge', 6: 'Rice Stemfly', 7: 'brown plant hopper', 8: 'white backed plant hopper', 9: 'small brown plant hopper',
    10: 'rice water weevil', 11: 'rice leafhopper', 12: 'grain spreader thrips', 13: 'rice shell pest', 14: 'grub', 15: 'mole cricket', 16: 'wireworm',
    17: 'white margined moth', 18: 'black cutworm', 19: 'large cutworm', 20: 'yellow cutworm', 21: 'red spider', 22: 'corn borer', 23: 'army worm', 24: 'aphids',
    25: 'Potosiabre vitarsis', 26: 'peach borer', 27: 'english grain aphid', 28: 'green bug', 29: 'bird cherry-oataphid', 30: 'wheat blossom midge',
    31: 'penthaleus major', 32: 'longlegged spider mite', 33: 'wheat phloeothrips', 34: 'wheat sawfly', 35: 'cerodonta denticornis', 36: 'beet fly',
    37: 'flea beetle', 38: 'cabbage army worm', 39: 'beet army worm', 40: 'Beet spot flies', 41: 'meadow moth', 42: 'beet weevil', 43: 'sericaorient alismots chulsky',
    44: 'alfalfa weevil', 45: 'flax budworm', 46: 'alfalfa plant bug', 47: 'tarnished plant bug', 48: 'Locustoidea', 49: 'lytta polita', 50: 'legume blister beetle',
    51: 'blister beetle', 52: 'therioaphis maculata Buckton', 53: 'odontothrips loti', 54: 'Thrips', 55: 'alfalfa seed chalcid', 56: 'Pieris canidia',
    57: 'Apolygus lucorum', 58: 'Limacodidae', 59: 'Viteus vitifoliae', 60: 'Colomerus vitis', 61: 'Brevipoalpus lewisi McGregor', 62: 'oides decempunctata',
    63: 'Polyphagotars onemus latus', 64: 'Pseudococcus comstocki Kuwana', 65: 'parathrene regalis', 66: 'Ampelophaga', 67: 'Lycorma delicatula', 68: 'Xylotrechus',
    69: 'Cicadella viridis', 70: 'Miridae', 71: 'Trialeurodes vaporariorum', 72: 'Erythroneura apicalis', 73: 'Papilio xuthus', 74: 'Panonchus citri McGregor',
    75: 'Phyllocoptes oleiverus ashmead', 76: 'Icerya purchasi Maskell', 77: 'Unaspis yanonensis', 78: 'Ceroplastes rubens', 79: 'Chrysomphalus aonidum',
    80: 'Parlatoria zizyphus Lucus', 81: 'Nipaecoccus vastalor', 82: 'Aleurocanthus spiniferus', 83: 'Tetradacus c Bactrocera minax', 84: 'Dacus dorsalis(Hendel)',
    85: 'Bactrocera tsuneonis', 86: 'Prodenia litura', 87: 'Adristyrannus', 88: 'Phyllocnistis citrella Stainton', 89: 'Toxoptera citricidus', 90: 'Toxoptera aurantii',
    91: 'Aphis citricola Vander Goot', 92: 'Scirtothrips dorsalis Hood', 93: 'Dasineura sp', 94: 'Lawana imitata Melichar', 95: 'Salurnis marginella Guerr',
    96: 'Deporaus marginatus Pascoe', 97: 'Chlumetia transversa', 98: 'Mango flat beak leafhopper', 99: 'Rhytidodera bowrinii white', 100: 'Sternochetus frigidus',
    101: 'Cicadellidae'
}

# Web Server Setup
app = Flask(__name__)
live_frame = None 
frame_counter = 0

def generate_stream():
    global live_frame
    while True:
        if live_frame is not None:
            ret, buffer = cv2.imencode('.jpg', live_frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        else:
            time.sleep(0.05)

@app.route('/video')
def video():
    return Response(generate_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False), daemon=True).start()

last_fire_time = 0
COOLDOWN_SECONDS = 5

# ==========================================
# 2. MAIN LOOP
# ==========================================
def loop():
    global live_frame, last_fire_time, frame_counter
    
    # Flush camera buffer to prevent queue delay
    for _ in range(2):
        cap.grab()
        
    ret, frame = cap.read()
    if not ret:
        return

    frame_counter += 1
    
    # Run AI every 2nd frame for maximum smoothness with 512x512
    if frame_counter % 2 == 0:
        input_size = 512  # Matches your new model specification
        img = cv2.resize(frame, (input_size, input_size))
        blob = img.transpose(2, 0, 1).astype(np.float32) / 255.0
        input_tensor = np.expand_dims(blob, axis=0)

        outputs = session.run(None, {input_name: input_tensor})
        predictions = np.squeeze(outputs[0]).T 

        for row in predictions:
            class_scores = row[4:]
            class_id = np.argmax(class_scores)
            confidence = class_scores[class_id]
            
            if confidence > 0.65:
                pest_name = CLASS_NAMES.get(class_id, f"Pest ID {class_id}")
                
                cx, cy, w_box, h_box = row[0], row[1], row[2], row[3]
                h_orig, w_orig, _ = frame.shape
                x1 = int((cx - w_box / 2) * (w_orig / input_size))
                y1 = int((cy - h_box / 2) * (h_orig / input_size))
                x2 = int((cx + w_box / 2) * (w_orig / input_size))
                y2 = int((cy + h_box / 2) * (h_orig / input_size))
                
                # Draw Box and Label
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                label = f"{pest_name} {int(confidence * 100)}%"
                cv2.putText(frame, label, (x1, max(y1 - 10, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                
                print(f"[MATCH FOUND] {pest_name} at {int(confidence * 100)}%!")
                
                current_time = time.time()
                if (current_time - last_fire_time) > COOLDOWN_SECONDS:
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    safe_name = pest_name.replace(" ", "_")
                    filename = os.path.join(snapshots_dir, f"{timestamp}_{safe_name}.jpg")
                    
                    cv2.imwrite(filename, frame)
                    print(f"[SNAPSHOT SAVED] Image saved to {filename}")
                    
                    # Bridge.call("engage", 90)
                    last_fire_time = current_time
                    
                break

    live_frame = frame.copy()

# ==========================================
# 3. EXECUTION
# ==========================================
App.run(user_loop=loop)