import json
from random import random
from time import time
import requests, threading
import paho.mqtt.client as PahoMQTT


#TODO: move these constants to a separate file 
# define topics in a coherent way

GROUP       = "group1" # group ID nececcary to distinguish the path among other groups (because of the broker is public)
BASE_TOPIC = f"/tiot/{GROUP}"

"""
    =========
    TOPICS 
    =========
"""
SENSOR_CONFIGURATION_BASE = f"{BASE_TOPIC}/configuration" #topic where the bridge will send the configuration to the sensor, an ID will be added at the end 
ACK_DEVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/ack" 
REGISTRATION_DEVICES_TOPIC = f"{BASE_TOPIC}/catalog/devices/registration"

class TempSenseMQTT:
    def __init__(self,url,clientID):
        self.clientID = clientID
        self.client = PahoMQTT.Client(clientID)
        self.url=url
        response = requests.get(f"{self.url}/broker")
        self.temp_thread = threading.Thread(target=self.temp_loop, daemon=True)
        metadata = response.json()
        self.broker = metadata["ip"]
        self.port = metadata["port"]
        self.interval = 30
        self.temperature_topic = f"{BASE_TOPIC}/{self.clientID}/temperature"
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):    
        print(f"Connected with result code {rc}")
        self.client.subscribe(f"{SENSOR_CONFIGURATION_BASE}/{self.clientID}", 0)
        self.client.subscribe(f"{ACK_DEVICES_TOPIC_BASE}/{self.clientID}", 0)
        device = {
            "id": self.clientID,
            "description": "Living room temperature sensor",
            "endpoint": "http://localhost:8080/sensor/temperature",
            "mqtt": {
                "ip": self.broker,
                "port": self.port,
                "topic": self.temperature_topic
            },
            "resources": ["temperature"],
            "time": time.time()
        }
    
        self.client.publish(REGISTRATION_DEVICES_TOPIC, json.dumps(device))



    def on_message(self, client, userdata, msg):
        try:
         payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            print("Received message is not a valid JSON")
            return
        self.interval = payload["interval"] if "interval" in payload else self.interval

    
def start(self):
        self.client.connect(self.broker, self.port)
        self.client.loop_start()
        
def temp_loop(self):
    while True:
            temp = random.uniform(20.0, 30.0)
            senml = [
                {
                    "bn": self.clientID,
                    "bt": time.time(),
                    "e": [
                        {
                            "n": "temperature",
                            "u": "Cel",
                            "v": temp
                        }
                    ]
                }
            ]

            self.client.publish(self.temperature_topic, json.dumps(senml))
            time.sleep(self.interval)