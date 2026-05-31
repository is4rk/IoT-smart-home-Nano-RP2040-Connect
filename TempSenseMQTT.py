import json
from random import random
from time import time
import requests, threading
import paho.mqtt.client as PahoMQTT
import CatalogClient 
from constants import *
#TODO: move these constants to a separate file 
# define topics in a coherent way

"""
    =========
    TOPICS 
    =========
"""
class TempSenseMQTT:
    def __init__(self,url,clientID):
        self.clientID = clientID
        self.client = PahoMQTT.Client(clientID)
        self.url=url
        catalogCli = CatalogClient(url)
        response = catalogCli.get_broker()
        metadata = response.json() if hasattr(response, 'json') else response
        self.broker = metadata["ip"]
        self.port = metadata["port"]
        self.interval = 30
        self.ack = False
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
                "pub_topic": self.temperature_topic,
                "sub_topic": f"{BASE_TOPIC}/{self.clientID}/commands/temperature"
            },
            "resources": ["temperature"],
            "time": time.time()
        }
    
        self.client.publish(REGISTRATION_DEVICES_TOPIC, json.dumps(device))



    def on_message(self, client, userdata, msg):
        topic = msg.topic
        if topic == f"{SENSOR_CONFIGURATION_BASE}/{self.clientID}":
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
            except json.JSONDecodeError:
                print("Received message is not a valid JSON")
                return
            self.interval = payload["interval"] if "interval" in payload else self.interval
        elif topic == f"{ACK_DEVICES_TOPIC_BASE}/{self.clientID}":
            self.ack = True

    
def start(self):
        self.client.connect(self.broker, self.port)
        self.client.loop_start()
        
def temp_loop(self):
    while True and self.ack:
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