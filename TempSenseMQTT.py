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
SENSOR_TEMPERATURE_BASE = f"{BASE_TOPIC}/temperature"


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
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc):    
        print(f"Connected with result code {rc}")
        self.client.subscribe(f"{SENSOR_CONFIGURATION_BASE}/{self.clientID}")


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

            self.client.publish(f"{SENSOR_TEMPERATURE_BASE}/{self.clientID}", json.dumps(senml))
            time.sleep(self.interval)