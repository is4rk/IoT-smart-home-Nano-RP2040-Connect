import paho.mqtt.client as PahoMQTT
import threading, time, uuid
import random, json
from constants import *


class DeviceMQTTClient:
    def __init__(self, clientID, broker, port):
        #TODO remeber that broker is no longer universal, maybe make utils file
        self.broker   = broker
        self.port     = port
        self.ack = False
        self.clientID = clientID
        self.client = PahoMQTT.Client(clientID)
        self.client.on_connect = self.on_connect  # sets the function called when the bridge connects to the broker
        self.client.on_message = self.on_message  # sets the function called when the bridge receives a message
        self.last_response=None

    def _random_device_payload(self):
        # Map these keys to the device JSON format defined in Catalog.py
        device_types = ["temperature_sensor", "humidity_sensor", "motion_sensor", "light_sensor", "switch", "smart_toilet"]
        rooms = ["kitchen", "living_room", "bedroom", "bathroom", "garage"]
        device_type = random.choice(device_types)
        room = random.choice(rooms)

        return {
            "id": self.clientID,
            "description": f"{device_type} in {room}",
            "endpoint": f"http://localhost:8080/{room}/{device_type}",
            "mqtt": {
                "ip": self.broker,
                "port": self.port,
                "pub_topics": [f"{BASE_TOPIC}/data/{self.clientID}"],
                "sub_topics": [
                    f"{ACK_DEVICES_TOPIC_BASE}/{self.clientID}",
                    f"{QUERY_RESPONSE_TOPIC_BASE}/{self.clientID}"
                ]
            },
            "resources": ["temperature", "humidity"],
            "time": time.time()
        }
    
    #TODO wait for MQTTCatalog, when its done finish case 2 and check other cases
    def _menu_loop(self):
        value = "1"
        while value != "4":
            print("(1) register now\n(2) query all devices\n(3) query device by ID\n(4) quit")
            value = input(": ").strip()
            match value:
                case "1":
                    payload = json.dumps(self._random_device_payload())
                    self.client.publish(REGISTRATION_DEVICES_TOPIC, payload)
                    print("[Device MQTT client] Registration sent")

                case "2":
                    request_id = str(uuid.uuid4())
                    payload = json.dumps({"client_id": self.clientID, "request_id": request_id})
                    self.client.publish(QUERY_ALL_DEVICES_TOPIC, payload)
                    print("[Device MQTT client] Query all devices not implemented yet")

                case "3":
                    device_id = input("Device ID: ").strip()
                    request_id = str(uuid.uuid4())
                    payload = json.dumps({"client_id": self.clientID, "request_id": request_id})
                    self.client.publish(f"{QUERY_DEVICE_BY_ID_TOPIC_BASE}/{device_id}", payload)
                    print(f"[Device MQTT client] Query for {device_id} sent")
                    time.sleep(1)
                    if self.last_response:
                        print(f"Response: {self.last_response}")
                        self.last_response = None


                case "4":
                    print("[Device MQTT client] Exiting menu")
               
                case _:
                    print("Invalid option")
    
    def _pub_reg_loop(self):
        while True:
            time.sleep(10) #stops deadlock :D
            if self.ack == True:
                time.sleep(60)
                payload = json.dumps(self._random_device_payload())
                self.client.publish(REGISTRATION_DEVICES_TOPIC, payload)

    def start(self): 
        self.client.connect(self.broker, self.port, keepalive=60) 
        self.client.loop_start() 
        threading.Thread(target=self._pub_reg_loop, daemon=True).start() #This is here to avoid a possible race condition. I cant wait to stop studying for O.S. T_T
        threading.Thread(target=self._menu_loop, daemon=True).start()
    
    def on_connect(self, client, userdata, flags, rc): #as said, it will handles the action when the bridge connect to the broker
        print(f"[Device MQTT client] Connected with result code {rc}")  # prints the connection result
        self.client.subscribe(f"{ACK_DEVICES_TOPIC_BASE}/{self.clientID}", 0);         print(f"[Device MQTT client] Subscribed to {ACK_DEVICES_TOPIC_BASE}/{self.clientID}")
        self.client.subscribe(f"{QUERY_RESPONSE_TOPIC_BASE}/{self.clientID}", 0);        print(f"[Device MQTT client] Subscribed to {QUERY_RESPONSE_TOPIC_BASE}/{self.clientID}")
        
    def on_message(self, client, userdata, msg):
        topic = msg.topic
        if topic == f"{ACK_DEVICES_TOPIC_BASE}/{self.clientID}":
            try:
                ack_payload = json.loads(msg.payload.decode("utf-8"))
                print(f"[Device MQTT client] ACK received: {ack_payload}")
            except Exception:
                print(f"[Device MQTT client] ACK received (non-JSON): {msg.payload!r}")
            self.ack = True

        else:
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
                print(f"[Device MQTT client] Received on {msg.topic}: {payload}")
                self.last_response = payload
            except json.JSONDecodeError:
                print("[Device MQTT client] Invalid JSON received")

if __name__ == "__main__":
    # Standard client deployment variables
    # (Pointing directly to your working public sandbox broker)
    BROKER_HOST = "test.mosquitto.org"
    BROKER_PORT = 1883
    UNIQUE_ID   = "smart_sensor_kitchen"
    # Instantiating matching your exact fixed signature layout
    device = DeviceMQTTClient(clientID=UNIQUE_ID, broker=BROKER_HOST, port=BROKER_PORT)
    device.start()

    # Keep main runtime wrapper block responsive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")