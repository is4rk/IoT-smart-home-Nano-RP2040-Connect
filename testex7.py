import time
import json
import threading
import paho.mqtt.client as PahoMQTT
from constants import *

# Configurations matching your bridge setup
BROKER = "test.mosquitto.org"
PORT = 1883
CLIENT_ID = "smart_sensor_kitchen"

class MQTTDeviceClient:
    def __init__(self):
        self.client = PahoMQTT.Client(CLIENT_ID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def start(self):
        self.client.connect(BROKER, PORT, 60)
        self.client.loop_start()
        
    def on_connect(self, client, userdata, flags, rc):
        print(f"Client connected to broker with code {rc}")
        # Subscribe to our own ACK and response channels
        self.client.subscribe(f"{ACK_DEVICES_TOPIC_BASE}/{CLIENT_ID}")
        self.client.subscribe(f"{QUERY_RESPONSE_TOPIC_BASE}/{CLIENT_ID}")

    def on_message(self, client, userdata, msg):
        print(f"\n[INCOMING MQTT MESSAGE] Topic: {msg.topic}")
        print(json.dumps(json.loads(msg.payload.decode()), indent=4))

    def register(self):
        payload = {
            "id": CLIENT_ID,
            "description": "Kitchen Gas & Temp Sensor",
            "resources": ["gas", "temperature"]
        }
        self.client.publish(REGISTRATION_DEVICES_TOPIC, json.dumps(payload))
        print("Registration message sent!")

    def heartbeat(self):
        payload = {"id": CLIENT_ID}
        self.client.publish(REFRESH_DEVICE_TOPIC, json.dumps(payload))
        print("Heartbeat update sent!")

    def query_all(self):
        payload = {"client_id": CLIENT_ID, "request_id": str(int(time.time()))}
        self.client.publish(QUERY_ALL_DEVICES_TOPIC, json.dumps(payload))
        print("Query all devices request sent!")

def heartbeat_loop(device):
    while True:
        time.sleep(60)
        device.heartbeat()

if __name__ == "__main__":
    device = MQTTDeviceClient()
    device.start()
    
    # Wait for connection setup
    time.sleep(1)
    
    # Start periodic background updates
    threading.Thread(target=heartbeat_loop, args=(device,), daemon=True).start()

    # Interactive Terminal Menutestex7.py

    while True:
        print("\n--- MQTT Interactive Client Test Menu ---")
        print("1. Send Initial Registration (POST via Bridge)")
        print("2. Send Periodic Heartbeat (PUT via Bridge)")
        print("3. Query All Registered Devices")
        print("4. Exit")
        choice = input("Select an option: ")

        if choice == "1":
            device.register()
        elif choice == "2":
            device.heartbeat()
        elif choice == "3":
            device.query_all()
        elif choice == "4":
            break
        time.sleep(1.5) # Brief pause to allow incoming messages to print cleanly