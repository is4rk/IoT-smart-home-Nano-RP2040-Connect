// usiamo il sensore di temperatura interno che da docs richiede questa libreria
#include <Arduino_LSM6DSOX.h>

void setup() {
  // se non si inizializza IMU, blocca
  if (!IMU.begin()) {
    Serial.println("Failed to initialize IMU!");
    while (1);
  }

  Serial.begin(9600);
  while (!Serial);
  Serial.println("Lab 1.5 starting - Internal Temperature Sensor");
  
}

void loop() {
  // modulo imu montato sulla scheda
  if (IMU.temperatureAvailable())
  {
    int temperature_deg = 0;
    // conversione gestita da libreria, ma int anzichè float
    IMU.readTemperature(temperature_deg);

    Serial.print("Temperature = ");
    Serial.print(temperature_deg);
    Serial.println(" °C");
  }
  delay(3000);
}
