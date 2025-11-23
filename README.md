# Autonomous-UAV-Sensor-Research-Platform
The goal of the project is the design, construction, and software development of an autonomous Unmanned Aerial Vehicle (UAV) to serve as a mobile research testbed. The project focuses on a comparative analysis of three obstacle detection technologies: laser (ToF), ultrasonic, and infrared (IR) under various operational conditions, taking into account vibrations, attitude changes (tilt), and electromagnetic interference.

Hardware Configuration

Flight Controller (FC): T-Motor Velox F7 SE Stack running ArduPilot firmware, responsible for stabilization and GPS navigation (Beitian BN-880).

Companion Computer (ESP32): A microcontroller acting as the primary research unit. It is responsible for sensor data acquisition and communication with the FC via the MAVLink protocol (UART).

Research Methodology The study involves autonomous flight missions directed towards a test wall covered with various materials. The algorithm implemented on the ESP32 executes a control loop consisting of:

Continuous data acquisition from sensors: TF-Luna (LIDAR), HC-SR04 (Ultrasonic), and Sharp GP2Y0A21YK (IR).

Real-time signal analysis.

Upon obstacle detection: stopping the time measurement and sending an RTL (Return to Launch) command to the flight controller to initiate a safe return of the drone.

Mechanical Design The design integrates off-the-shelf carbon fiber components with custom parts designed in Fusion 360 and manufactured using FDM 3D printing technology (PETG). This includes a modular sensor panel, a GPS mast, and a dedicated "deck" for the research electronics, designed to optimize the Center of Gravity (CoG) and minimize the impact of vibrations on measurements.
