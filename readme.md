To use this on an actual arduino nano RP2040 connect, upload the .ino from exercise 10. and make it run. Then on a pc, run the main.py, (runs MQTT, REST and Log). 
The parameters that need changing are in constants.py (ip adress and port number), put the same ones in the arduino file. Remeber to also generate an arduino_secretes.h with wifi name and password.
For any bugs, open an issue.

Exercise 0:
[main file](main.py)

Exercise 1:
[Smart home sensosr service with out uri](SmartHomeSensorServiceNoUri.py)

Exercise 2:
[Smart home sensor Service](SmartHomeSensorService.py)

Exercise 3:
[Smart home sensor Service and Actuator Service](SmartHomeSensorService.py)

Exercise 4:
[Event log service REST](EventLog.py)

Exercise 5:
[Catalog.py](Catalog.py)

Exercise 6:
[S.H.S.S and A.S. with Catalog](SmartHomeSensorService.py)
[Catalog client](CatalogClient.py)

Exercise 7:
[MQTT bridge to Catalog](MQTTCatalogBridge.py)

Exercise 8:
[MQTT device client](DeviceMQTTClient.py)

Exercise 9: 
[MQTT Temperature Publisher](TempSenseMQTT.py)

Exercise 10:
[Arduino Registration on the Catalog](lab_3.3_ex10/lab_3.3_ex10.ino)

Exercise 11:
[MQTT actuator command publisher](MQTTActuatorCommandPublisher.py)
[Bridge used for actuator](MQTTActuatorBridge.py)

Exercise 12:
[Event Log Service MQTT](EventLog.py)

Exercise 13:
[Integrated Smart Home Controller](SmartHomeController13.py)
[Arduino part](lab_3.3_ex13_arduino/lab_3.3_ex13_arduino.ino)

Exercise 14:
[Integrated Smart Home Controller with former Arduino features](SmartHomeController14.py)
[Arduino part](lab_3.3_ex14_remote_arduino/lab_3.3_ex14_remote_arduino.ino)
