#include <Arduino.h>

// --- PIN CONFIGURATION ---
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;
const int LED_PIN  = 2;

// --- CONSTANTS ---
const float SOUND_SPEED = 0.034;
const unsigned long PAUSE_TIME = 10000; // 10 seconds lock
const float TRIGGER_THRESHOLD = 5.0;    // Trigger distance in cm
unsigned long Sys_start_time = 0;
const unsigned long ARMING_DELAY = 5000;  //5 sec delay for sensor to start measuring 


// --- SENSOR DATA STRUCTURE ---
struct SensorNode {
    String techName;
    float currentDistance;
    float snapshotResult;
};

// Array to store data for 3 different technologies
SensorNode sensors[3] = {
    {"ULTRASONIC", 0.0, 0.0},
    {"LASER_TOF",  0.0, 0.0},
    {"INFRARED",   0.0, 0.0}
};

// --- GLOBAL VAR
volatile unsigned long echoStart = 0;
volatile unsigned long echoDuration = 0;
volatile bool newMeasurementReady = false;
int measurementCounter = 1;

bool isLocked = false;
unsigned long lockStartTime = 0;
int lastCountdownSecond = -1;

// --- INTERRUPT SERVICE ROUTINE (ISR) ---
void IRAM_ATTR echoISR() {
    if (digitalRead(ECHO_PIN) == HIGH) {
        echoStart = micros();
    } else {
        echoDuration = micros() - echoStart;
        newMeasurementReady = true;
    }
}

// --- HELPER FUNCTIONS ---
void printSnapshotTable() {
    Serial.println("\n>> SNAPSHOT REPORT <<");
    Serial.println("| TECHNOLOGY   | DISTANCE [cm] |");
    Serial.println("|--------------|---------------|");
    for (int i = 0; i < 3; i++) {
        Serial.printf("| %-12s | %-13.2f |\n", sensors[i].techName.c_str(), sensors[i].snapshotResult);
    }
    Serial.println("--------------------------------\n");
}

void setup() {
    Serial.begin(115200);
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);
    pinMode(LED_PIN, OUTPUT);
    Sys_start_time = millis();  
    Serial.println("SYSTEM_INITIALIZING_WAIT_3S...");
    attachInterrupt(digitalPinToInterrupt(ECHO_PIN), echoISR, CHANGE);  
    Serial.println("SYSTEM_INITIALIZED");

}

void loop() {
    unsigned long currentMillis = millis();
    bool thresholdReached = false;

    if (currentMillis - Sys_start_time > ARMING_DELAY){ //.......avoiding valid measurements at the start
        for (int i = 0; i < 3; i++){
            if (sensors[i].currentDistance > 0 && sensors[i].currentDistance <= TRIGGER_THRESHOLD){
                thresholdReached = true;
                break;
            }
        }
    }

    if (!isLocked) {
        digitalWrite(LED_PIN, LOW);
        static unsigned long lastTriggerTime = 0;

        if (currentMillis - lastTriggerTime >= 50) {
            digitalWrite(TRIG_PIN, LOW);
            delayMicroseconds(2);
            digitalWrite(TRIG_PIN, HIGH);
            delayMicroseconds(10);
            digitalWrite(TRIG_PIN, LOW);
            lastTriggerTime = currentMillis;
        }

        if (newMeasurementReady) {
            sensors[0].currentDistance = echoDuration * SOUND_SPEED / 2;
            newMeasurementReady = false;
        }

        // Teleplot Real-time Visualization
        for (int i = 0; i < 3; i++) {
            Serial.print(">");
            Serial.print(sensors[i].techName);
            Serial.print(":");
            Serial.println(sensors[i].currentDistance);
        }

        bool thresholdReached = false;
        for (int i = 0; i < 3; i++) {
            if (sensors[i].currentDistance > 0 && sensors[i].currentDistance <= TRIGGER_THRESHOLD) {
                thresholdReached = true;
                break;
            }
        }

        if (thresholdReached) {
            for (int i = 0; i < 3; i++) {
                sensors[i].snapshotResult = sensors[i].currentDistance;
            }
            
            // LINIA DO EXCELA: Wypisuje tylko raz przy wykryciu
            Serial.print("DATA,"); // Nagłówek dla łatwego filtrowania
            Serial.print(sensors[0].snapshotResult); Serial.print(",");
            Serial.print(sensors[1].snapshotResult); Serial.print(",");
            Serial.println(sensors[2].snapshotResult);

            printSnapshotTable();
            isLocked = true;
            lockStartTime = currentMillis;
            lastCountdownSecond = -1;
        }

    } else {
        digitalWrite(LED_PIN, HIGH);
        
        unsigned long elapsed = currentMillis - lockStartTime;
        
        // Faza 1: Odliczanie 10 sekund
        if (elapsed < PAUSE_TIME) {
            int secondsLeft = (PAUSE_TIME - elapsed) / 1000;
            if (secondsLeft != lastCountdownSecond) {
                Serial.print(">countdown:");
                Serial.println(secondsLeft);
                lastCountdownSecond = secondsLeft;
            }
        } 
        // Faza 2: Czekanie na zabranie przeszkody przed odblokowaniem
        else {
            digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10); digitalWrite(TRIG_PIN, LOW);
            long checkDuration = pulseIn(ECHO_PIN, HIGH, 30000);
            float checkDist = checkDuration * SOUND_SPEED / 2;

            if (checkDist > TRIGGER_THRESHOLD || checkDuration == 0) {
                isLocked = false;
                Serial.println("SYSTEM_RESTART_READY");
                Serial.println(">countdown:0");
            } else {
                
                Serial.println(">status:WAITING_FOR_CLEAR"); 
            }
        }
    }
}