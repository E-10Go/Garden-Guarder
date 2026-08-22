#include <Servo.h>
#include "Arduino_RouterBridge.h"

// --- Pin Definitions ---
const int pumpRelayPin = 2;  // Relay connected to Pin 2
const int buzzerPin    = 3;     // Buzzer connected to Pin 3
const int servoPin     = 4;     // Aiming Servo connected to Pin 4

// Left Motors (OUT1 & OUT2)
const int motorIN1 = 5;
const int motorIN2 = 6;
const int speedPinL = 9;  // ENA (PWM)

// Right Motors (OUT3 & OUT4)
const int motorIN3 = 7;
const int motorIN4 = 8;
const int speedPinR = 10; // ENB (PWM)

int searchSpeed = 70;   // Slower speed for steady searching/inching forward
int turnSpeed = 90;     // Speed for turning
Servo aimingServo;

void setup() {
  Monitor.begin(115200); 
  Bridge.begin(); 
  
  pinMode(pumpRelayPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);
  
  pinMode(motorIN1, OUTPUT);
  pinMode(motorIN2, OUTPUT);
  pinMode(motorIN3, OUTPUT);
  pinMode(motorIN4, OUTPUT);
  pinMode(speedPinL, OUTPUT);
  pinMode(speedPinR, OUTPUT);

  aimingServo.attach(servoPin);
  aimingServo.write(90); // Center servo position
  
  stopMotors();
  digitalWrite(pumpRelayPin, HIGH); // HIGH keeps relay OFF (change to LOW if Active-High)
  digitalWrite(buzzerPin, LOW);    
  
  // --- Expose Functions to Python via Bridge ---
  Bridge.provide("test", performSelfTest);
  Bridge.provide("startSearch", startSlowSearch);
  Bridge.provide("engage", executeFiringSequence);
  Bridge.provide("stop", stopMotors);
}

void loop() {
  // Bridge handles incoming RPC commands automatically in the background.
}

// ==========================================
// --- HARDWARE SEQUENCES ---
// ==========================================

void performSelfTest() {
  Monitor.println("Running Diagnostic Test...");
  aimingServo.write(45); delay(300);
  aimingServo.write(135); delay(300);
  aimingServo.write(90); delay(300);
  
  digitalWrite(buzzerPin, HIGH); delay(100);
  digitalWrite(buzzerPin, LOW); delay(100);
  
  digitalWrite(pumpRelayPin, LOW); delay(150);
  digitalWrite(pumpRelayPin, HIGH); delay(100);
  
  startSlowSearch(); delay(300);
  stopMotors();
  Monitor.println("Test Complete!");
}

// Moves slowly forward searching for targets
void startSlowSearch() {
  analogWrite(speedPinL, searchSpeed);
  analogWrite(speedPinR, searchSpeed);
  
  digitalWrite(motorIN1, HIGH);
  digitalWrite(motorIN2, LOW);
  digitalWrite(motorIN3, HIGH);
  digitalWrite(motorIN4, LOW);
}

void executeFiringSequence(int angle) {
  Monitor.println("Target detected! Stopping, turning, and spraying...");
  
  // 1. Stop moving forward instantly upon detection
  stopMotors();
  delay(200);
  
  // 2. Sound Buzzer Alert
  digitalWrite(buzzerPin, HIGH); 
  delay(1000);
  digitalWrite(buzzerPin, LOW);
  
  // 3. Turn slightly right (~20 degrees adjustment)
  analogWrite(speedPinL, turnSpeed);
  analogWrite(speedPinR, turnSpeed);
  digitalWrite(motorIN1, HIGH);
  digitalWrite(motorIN2, LOW);
  digitalWrite(motorIN3, LOW);
  digitalWrite(motorIN4, HIGH);
  delay(250); // Adjust this delay if 20 degrees needs fine-tuning
  stopMotors();
  delay(200);
  
  // 4. Aim Nozzle via Servo
  aimingServo.write(angle); 
  delay(400); 
  
  // 5. Trigger Pump Relay to spray water for 3 seconds
  digitalWrite(pumpRelayPin, LOW); // LOW activates relay
  delay(3000); 
  digitalWrite(pumpRelayPin, HIGH); // Turn pump off
  
  // 6. Reset Servo to center
  aimingServo.write(90);
  
  // 7. Turn away completely (180-degree spin) to head in the opposite direction
  Monitor.println("Spraying complete. Turning around to scan opposite direction...");
  analogWrite(speedPinL, turnSpeed);
  analogWrite(speedPinR, turnSpeed);
  digitalWrite(motorIN1, HIGH);
  digitalWrite(motorIN2, LOW);
  digitalWrite(motorIN3, LOW);
  digitalWrite(motorIN4, HIGH);
  delay(1100); // ⚠️ Adjust this delay time so it performs a clean 180-degree turn on your specific chassis
  stopMotors();
  delay(300);
  
  // 8. Resume searching forward in the new direction
  Monitor.println("Resuming search in opposite direction.");
  startSlowSearch();
}

// ==========================================
// --- MOTOR HELPER FUNCTIONS ---
// ==========================================

void stopMotors() {
  analogWrite(speedPinL, 0);
  analogWrite(speedPinR, 0);
  digitalWrite(motorIN1, LOW);
  digitalWrite(motorIN2, LOW);
  digitalWrite(motorIN3, LOW);
  digitalWrite(motorIN4, LOW);
}