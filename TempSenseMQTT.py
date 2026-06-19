import json
import random
import time
import requests, threading
import paho.mqtt.client as PahoMQTT
from CatalogClient import CatalogClient 
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
        self.device_payload = self.build_device_payload()
        self.client.publish(REGISTRATION_DEVICES_TOPIC, json.dumps(self.device_payload))
    


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
            threading.Thread(target=self.temp_loop, daemon=True).start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
            
    def temp_loop(self):
        print("[Sensor] Telemetry and Heartbeat engine started.")
        while True:
            if self.ack:
                # 1. Send Telemetry Data
                temp = random.uniform(20.0, 30.0)
                senml = [
                    {
                        "bn": self.clientID,
                        "bt": time.time(),
                        "e": [{"n": "temperature", "u": "Cel", "v": temp}]
                    }
                ]
                self.client.publish(self.temperature_topic, json.dumps(senml))
                self.client.publish(f"{BASE_TOPIC}/log", json.dumps(senml))
                print(f"[Sensor] Telemetry sent: {round(temp, 2)}°C")

                # 2. Send Heartbeat
                self.device_payload = self.build_device_payload()
                self.client.publish(REFRESH_DEVICE_TOPIC, json.dumps(self.device_payload))
                print("[Sensor] Heartbeat refresh published to Bridge.")

                time.sleep(self.interval)
            else:
                # Wait for initial registration ACK before starting
                time.sleep(1)


    def build_device_payload(self):
        return {
            "id": self.clientID,
            "description": "Living room temperature sensor",
            "endpoint": "http://localhost:9966/sensor/temperature",
            "mqtt": {
                "ip": self.broker,
                "port": self.port,
                "pub_topics": [self.temperature_topic],
                "sub_topics": [
                    f"{SENSOR_CONFIGURATION_BASE}/{self.clientID}",
                    f"{ACK_DEVICES_TOPIC_BASE}/{self.clientID}"
                ]
            },
            "resources": ["temperature"],
            "time": time.time()
        }

if __name__ == "__main__":
    sensor = TempSenseMQTT(url=CATALOG_URL, clientID="temp_sensor_livingroom")
    sensor.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Sensor] Shutting down sensing layout.")