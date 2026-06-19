# Arduino Sketch For SW Exercise 14

This is the second Arduino sketch requested by Exercise 14. It keeps low-level hardware duties on the board and moves policy decisions to `SmartHomeControllerV2.py`.

## Before Uploading

Update these constants in `lab_3.3_ex14_remote_arduino.ino`:

```cpp
const char CATALOG_HOST[] = "10.120.246.215";
const int CATALOG_PORT = 8080;
```

`CATALOG_HOST` must be the LAN IP of the PC running `python main.py`.

Also make sure `arduino_secrets.h` exists in the same sketch folder or in your Arduino include path:

```cpp
#define SECRET_SSID "..."
#define SECRET_PASS "..."
```

## Required Libraries

- WiFiNINA
- ArduinoJson
- PubSubClient
- ArduinoHttpClient
- LiquidCrystal_PCF8574
- PDM

## Hardware Pins

- `A3`: temperature sensor
- `12`: PIR input
- `2`: green LED
- `A1`: heater LED/PWM
- `A2`: fan PWM
- I2C LCD at address `0x27`

## MQTT Behavior

Publishes:

- `tiot/group1/arduino_group1_ex14/temperature`
- `tiot/group1/arduino_group1_ex14/presence`
- `tiot/group1/arduino_group1_ex14/noise`
- feedback topics for led/fan/heater

Subscribes:

- `tiot/group1/arduino_group1_ex14/commands/led`
- `tiot/group1/arduino_group1_ex14/commands/fan`
- `tiot/group1/arduino_group1_ex14/commands/heater`
- `tiot/group1/arduino_group1_ex14/commands/lcd`

## Test Order

1. Run `python main.py`.
2. Upload this sketch.
3. Run `python SmartHomeControllerV2.py`.
4. Watch Serial Monitor for sensor publishes and received commands.

