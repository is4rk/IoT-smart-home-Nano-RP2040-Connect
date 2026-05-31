from random import random
import threading
import json
import time
import paho.mqtt.client as PahoMQTT
import requests
from constants import *

GROUP       = "group1" # group ID nececcary to distinguish the path among other groups (because of the broker is public)
BASE_TOPIC = f"/tiot/{GROUP}"

SENSOR_CONFIGURATION_BASE = f"{BASE_TOPIC}/configuration" #topic where the bridge will send the configuration to the sensor, an ID will be added at the end 
ACK_DEVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/ack" 
REGISTRATION_DEVICES_TOPIC = f"{BASE_TOPIC}/catalog/devices/registration"
QUERY_RESPONSE_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/query/response" 

class FakeArduinoMQTT:
    def __init__(self, clientID, url):
        self.clientID = clientID
        self.led_state = False  
        self.client = PahoMQTT.Client(clientID)
        self.url=url
        self.subs = []
        response = requests.get(f"{self.url}/broker")
        metadata = response.json()
        self.broker = metadata["ip"]
        self.port = metadata["port"]
        self.temp_thread = threading.Thread(target=self.temp_loop, daemon=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.led_topic = f"{BASE_TOPIC}/{self.clientID}/led"
        self.temperature_topic = f"{BASE_TOPIC}/{self.clientID}/temperature"
    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
        self.client.subscribe(f"{QUERY_RESPONSE_TOPIC_BASE}/{self.clientID}")
        self.client.subscribe(f"{ACK_DEVICES_TOPIC_BASE}/{self.clientID}")
        self.client.subscribe(self.led_topic)
        device = {
            "id": self.clientID,
            "description": "Living room temperature sensor",
            "endpoint": "http://localhost:8080/sensor/temperature",
            "mqtt": {
                "ip": self.broker,
                "port": self.port,
                "topic": [self.temperature_topic, self.led_topic]
            },
            "resources": ["temperature", "led"],
            "time": time.time()
        }
        self.client.publish(REGISTRATION_DEVICES_TOPIC, json.dumps(device))
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        if topic == f"{QUERY_RESPONSE_TOPIC_BASE}/{self.clientID}":
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
            except json.JSONDecodeError:
                print("Error: Invalid JSON in message payload")
                self.subs = payload["topic"] if "topic" in payload else []
                
        elif topic == self.led_topic:
            self.led_state = not self.led_state  
            
    def temp_loop(self):
        while True:
            time.sleep(60)
            device = {
            "id": self.clientID,
            "description": "Living room temperature sensor",
            "endpoint": "http://localhost:8080/sensor/temperature",
            "mqtt": {
                "ip": self.broker,
                "port": self.port,
                "topic": [self.temperature_topic, self.led_topic]
            },
            "resources": ["temperature", "led"],
            "time": time.time()
            }
            self.client.publish(REGISTRATION_DEVICES_TOPIC, json.dumps(device))             


    def start(self):
        self.client.connect(self.broker, self.port)
        self.temp_thread.start()
        self.client.loop_start()


    def temperature_loop(self):
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
            time.sleep(10)  