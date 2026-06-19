# Arduino Sketch For SW Exercise 13

This sketch is the Arduino counterpart for `SmartHomeController.py`.

It exposes the data needed by Exercise 13:

- publishes temperature readings in SenML;
- publishes motion readings in SenML;
- registers itself on the Catalog through the MQTT catalog bridge;
- receives remote LED commands through MQTT;
- publishes LED feedback.

## Before Uploading

Update the Catalog host in `lab_3.3_ex13_arduino.ino`:

```cpp
const char CATALOG_HOST[] = "10.120.246.215";
const int CATALOG_PORT = 8080;
```

`CATALOG_HOST` must be the LAN IP of the PC running:

```powershell
python .\main.py
```

Create `arduino_secrets.h` in this sketch folder:

```cpp
#pragma once
#define SECRET_SSID "YOUR_WIFI_SSID"
#define SECRET_PASS "YOUR_WIFI_PASSWORD"
```

## Topics

Publishes:

- `tiot/group1/arduino_group1_ex13/temperature`
- `tiot/group1/arduino_group1_ex13/motion`
- `tiot/group1/arduino_group1_ex13/feedback/led`

Subscribes:

- `tiot/group1/arduino_group1_ex13/commands/led`

## Test Order

1. Run `python .\main.py`.
2. Upload this sketch.
3. Run `python .\SmartHomeController.py`.
4. Watch the controller logs: it should receive temperature/motion and publish LED commands.

