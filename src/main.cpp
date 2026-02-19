#include <Arduino.h>
#include <Wire.h>
#include <VL53L0X.h>

// --- PINY ---
#define TRIG_PIN 18
#define ECHO_PIN 5
#define SHARP_PIN 35
#define LED_PIN 2 

VL53L0X laser;

const int LASER_OFFSET = 20; 
const float SHARP_CONST = 10000.0; 

// --- PARAMETRY (Zmienne, nie const!) ---
int triggerDistMm = 120; // Domyślnie 12 cm, ale można zmienić z aplikacji
const int RESET_DIST_MM = 300;   
const unsigned long DATA_SEND_INTERVAL = 50; 

enum AppState { MONITORING, OBSTACLE_HIT, WAITING, RESETTING };
AppState currentState = MONITORING;

unsigned long stateTimer = 0;      
unsigned long lastDataSend = 0;    

float ultraMm = 0;
float sharpMm = 0;
int laserMm = 0;
int triggerSource = 0; 

void setup() {
  Serial.begin(115200);
  Wire.begin();
  
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  analogReadResolution(12);

  if (!laser.init()) {
    // Laser init fail
  }
  laser.setTimeout(500);
  laser.startContinuous();
}

void readSensors() {
  // 1. ULTRA
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(15);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 25000); 
  ultraMm = (duration * 0.034 / 2.0) * 10.0;

  // 2. SHARP
  int s_raw = analogRead(SHARP_PIN);
  sharpMm = (s_raw < 100) ? 800.0 : (SHARP_CONST * pow(s_raw, -1.15)) * 100.0;
  if (sharpMm > 800) sharpMm = 800; 

  // 3. LASER
  laserMm = laser.readRangeContinuousMillimeters();
  if (laser.timeoutOccurred()) laserMm = 8190;
  else laserMm -= LASER_OFFSET;
  if (laserMm < 0) laserMm = 0;
}

void loop() {
  // --- ODBIERANIE KOMEND Z APLIKACJI ---
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim(); // Usuń spacje i znaki nowej linii
    
    // Jeśli komenda zaczyna się od "T" (np. "T200")
    if (cmd.startsWith("T")) {
      int newVal = cmd.substring(1).toInt();
      if (newVal >= 50 && newVal <= 800) { // Zabezpieczenie zakresu
        triggerDistMm = newVal;
        // Opcjonalnie: mrugnij LEDem na potwierdzenie
        digitalWrite(LED_PIN, !digitalRead(LED_PIN)); 
        delay(50);
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
      }
    }
  }

  readSensors();

  switch (currentState) {
    case MONITORING: {
      digitalWrite(LED_PIN, LOW);
      triggerSource = 0;

      // Używamy zmiennej triggerDistMm zamiast stałej
      bool s_hit = (sharpMm <= triggerDistMm);
      bool l_hit = (laserMm <= triggerDistMm && laserMm > 0);

      if (s_hit || l_hit) {
        if (s_hit && l_hit) triggerSource = 3;
        else if (s_hit) triggerSource = 1;
        else if (l_hit) triggerSource = 2;
        currentState = OBSTACLE_HIT;
      }
      break;
    }

    case OBSTACLE_HIT:
      digitalWrite(LED_PIN, HIGH);
      // Wysyłamy status "1" + aktualny triggerDistMm (żeby aplikacja wiedziała jaki był próg)
      Serial.printf("D;%.0f;%.0f;%d;1;%d;%d\n", ultraMm, sharpMm, laserMm, triggerSource, triggerDistMm);
      stateTimer = millis(); 
      currentState = WAITING; 
      break;

    case WAITING:
      if (millis() - stateTimer >= 10000) {
        digitalWrite(LED_PIN, LOW);
        currentState = RESETTING;
      }
      break;

    case RESETTING:
      if (sharpMm > RESET_DIST_MM && laserMm > RESET_DIST_MM) {
        currentState = MONITORING;
      }
      break;
  }

  if (millis() - lastDataSend >= DATA_SEND_INTERVAL) {
    lastDataSend = millis();
    if (currentState != OBSTACLE_HIT) {
      int statusToSend = 0;
      if (currentState == WAITING) statusToSend = 2;
      else if (currentState == RESETTING) statusToSend = 3;
      
      // Dodajemy aktualny próg (triggerDistMm) na końcu wiadomości
      Serial.printf("D;%.0f;%.0f;%d;%d;%d;%d\n", ultraMm, sharpMm, laserMm, statusToSend, triggerSource, triggerDistMm);
    }
  }
}