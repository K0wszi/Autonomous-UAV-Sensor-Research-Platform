# Autonomous-UAV-Sensor-Research-Platform
Platforma badawcza do analizy sensorów zbliżeniowych w różnych warunkach lotu. Projekt wykonywany w ramach pracy magisterskiej
Celem projektu jest zaprojektowanie, budowa oraz oprogramowanie autonomicznej platformy latającej (UAV), służącej jako mobilne stanowisko badawcze. Projekt skupia się na analizie porównawczej trzech technologii detekcji przeszkód: laserowej (ToF), ultradźwiękowej oraz podczerwieni (IR) w różnych warunkach operacyjnych, uwzględniających wibracje, przechyły oraz zakłócenia elektromagnetyczne.
Kontroler Lotu (FC): Stack T-Motor Velox F7 SE pracujący pod kontrolą oprogramowania ArduPilot, odpowiedzialny za stabilizację i nawigację GPS (Beitian BN-880).

Companion Computer (ESP32): Mikrokontroler pełniący rolę jednostki badawczej. Odpowiada za akwizycję danych z sensorów oraz komunikację z FC poprzez protokół MAVLink (UART).

Metodologia Badań

Badanie polega na autonomicznych misjach lotniczych w kierunku ściany testowej pokrytej różnymi materiałami. Algorytm zaimplementowany na ESP32 realizuje pętlę sterowania:

Ciągły odczyt danych z sensorów: TF-Luna (LIDAR), HC-SR04 (Ultradźwięki), Sharp GP2Y0A21YK (IR).

Analiza sygnału w czasie rzeczywistym.

W momencie detekcji przeszkody: zatrzymanie pomiaru czasu i wysłanie komendy RTL (Return to Launch) do kontrolera lotu, inicjującej bezpieczny powrót drona.

 Konstrukcja Mechaniczna

Projekt integruje gotowe elementy z włókna węglowego z autorskimi częściami zaprojektowanymi w Fusion 360 i wydrukowanymi w technologii FDM (PETG). Obejmuje to modułowy panel sensorów, maszt GPS oraz dedykowane "piętro" dla elektroniki badawczej, zaprojektowane w celu optymalizacji środka ciężkości (CoG) i minimalizacji wpływu wibracji na pomiary.
