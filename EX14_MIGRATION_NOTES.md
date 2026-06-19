# Exercise 14 - Migration Notes

Exercise 14 asks which former Arduino-side features from Hardware Lab 2.1 can move to the remote Integrated Smart Home Controller.

## Keep On Arduino

- Read physical sensors: temperature, PIR presence, microphone/noise.
- Publish sensor readings via MQTT in SenML format.
- Apply low-level actuation commands received via MQTT: heater LED/PWM, fan PWM, green LED, LCD text.
- Register as an IoT device and refresh registration.
- Retrieve broker and catalog metadata via REST.

These features depend on pins, interrupts, peripherals, or local display hardware.

## Move To Remote Controller

- Presence fusion: combine PIR and microphone/noise into a room occupancy state.
- Temperature policy and thresholds.
- Fan speed and heater intensity calculation.
- Alert generation.
- Rolling statistics.
- LCD page/message content decision.
- Setpoint/configuration management.

These features are policy decisions and are easier to tune remotely.

## Resulting Architecture

- Arduino v2 publishes `temperature`, `presence`, and `noise` to MQTT.
- Controller v2 subscribes to those readings.
- Controller v2 computes the fan/heater/LED/LCD commands.
- Arduino v2 receives command topics and applies them to hardware.

