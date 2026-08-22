# Garden-Guarder
a rover based AI guardian for gardens. It can detect pests using a simple pretrained model from the web and respond by aiming and spraying, so a garden can be watched and protected without someone standing over it all day.

## What this is

This project pairs a small rover chassis with a camera and an ONNX-based object detection model (trained on the IP102 pest dataset) to patrol a garden, spot pests in real time, and trigger a physical response — turning toward the pest, aiming a nozzle, and spraying — while also saving a snapshot of every detection.

The system has two halves:

- **Python (`app.py`, runs on the Arduino app-capable board / companion computer):** captures video, runs the ONNX model on each frame, draws detection boxes, streams live video over HTTP, saves snapshots, and talks to the Arduino over the Router Bridge.
- **Arduino sketch (`Sketch.ino`):** controls the physical hardware — drive motors, aiming servo, buzzer, and pump relay — and exposes a small set of functions the Python side can call remotely.

## How it works

1. The rover drives forward slowly in a search pattern (`startSearch`).
2. Every other frame from the camera is run through the ONNX model at 512x512 resolution.
3. If a detection's confidence is above 0.65, a bounding box and label are drawn on the live feed, a snapshot is saved to the `snapshots/` folder, and (once wired up — see Known Issues) the Arduino is told to engage.
4. On engage, the Arduino stops, sounds a buzzer, turns slightly, aims the nozzle servo, runs the pump for a few seconds, resets the servo, spins 180 degrees, and resumes searching in the opposite direction.
5. The live annotated video feed is available at all times over HTTP at `/video`, so you can watch what the rover sees from a browser on the same network.

## Hardware

| Component | Arduino Pin |
|---|---|
| Pump relay | 2 |
| Buzzer | 3 |
| Aiming servo | 4 |
| Left motor IN1 | 5 |
| Left motor IN2 | 6 |
| Left motor speed (PWM) | 9 |
| Right motor IN3 | 7 |
| Right motor IN4 | 8 |
| Right motor speed (PWM) | 10 |

Plus: a USB camera connected to the companion computer running the Python script, and a chassis with two motor channels (left/right, each driving one or more DC motors through a driver board).

## Software setup

1. Flash `Sketch.ino` to the Arduino board using the standard Arduino IDE or CLI, with the `Servo` and `Arduino_RouterBridge` libraries installed.
2. On the companion computer (the board running the Arduino App / Python side):
   - Place your trained model file as `best1.onnx` in the same folder as `app.py`.
   - Install dependencies: `opencv-python`, `onnxruntime`, `numpy`, `flask`.
   - Run the app through the Arduino App framework (`App.run(user_loop=loop)` handles the main loop and bridge connection).
3. Once running, open `http://<companion-computer-ip>:5000/video` in a browser to view the live annotated feed.
4. Detection snapshots are saved automatically to a `snapshots/` folder next to `app.py`, named with a timestamp and the detected pest's name.

## Model

The detection model is expected to be a YOLO-style ONNX export trained on 512x512 input images, outputting 4 box coordinates plus one confidence score per class. The full IP102 class list (102 pest species) is baked into `app.py` as `CLASS_NAMES`; if you swap in a different model, update this dictionary to match your model's class order.

## Known issues and things to fix before relying on this in the field

- **The spray trigger is currently disabled.** The call that tells the Arduino to fire (`Bridge.call("engage", 90)`) is commented out in `app.py`, so right now the rover only detects, displays, and photographs pests — it does not yet spray them. Uncomment and wire this up once you've tested the Arduino side in isolation.
- **No aiming calculation yet.** The angle passed to `engage` is hardcoded rather than computed from where the pest actually is in the frame.
- **Only the first detection per frame is acted on**, and there's no overlap suppression (NMS) if that gets extended to multiple detections.
- **No failsafe if the connection between the two sides drops** — the rover will keep driving on its last command. Consider adding a timeout that stops the motors if no heartbeat is received.
- **Servo and motor PWM share a timer on classic AVR boards.** Attaching the aiming servo can affect PWM quality on pins 9 and 10 (motor speed). Test motor smoothness with the servo attached before trusting it in the garden.
- **Relay polarity is unconfirmed** — verify HIGH/LOW behavior on your specific relay module before running the full firing sequence unattended.

## Safety notes

This rover controls a motorized platform and a water pump autonomously. Before letting it run unattended:

- Test each hardware function individually using the `test` command (`performSelfTest`) first.
- Keep it within a fenced or supervised area until you're confident in its behavior.
- Make sure the pump only sprays water (or whatever your intended safe substance is) — do not connect anything hazardous to this system without additional safeguards.
