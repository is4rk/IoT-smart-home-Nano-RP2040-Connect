import paho.mqtt.client as PahoMQTT
import threading, time
import random, json
BROKER      = "iot.eclipse.org" # public broker that we have to use
PORT        = 1883 # port to use to connect to the broker
GROUP       = "group1" # group ID nececcary to distinguish the path among other groups (because of the broker is public)
BASE_TOPIC = f"/tiot/{GROUP}"
REGISTRATION_DEVICES_TOPIC = f"{BASE_TOPIC}/catalog/devices/registration"  # Topic where devices publish their registrations; the bridge will subscribe to it and will handles the communication with the catalog
ACK_DEVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/ack"  # As required, the bridge has to send an ACK to the specific device after registration 
RESPONSE_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/response"

class DeviceMQTTClient:
    def __init__(self, clientID, broker, port):
        self.broker   = broker
        self.port     = port
        self.clientID = clientID
        self.client = PahoMQTT.Client(clientID) 
        self.client.on_connect = self.on_connect  # sets the function called when the bridge connects to the broker
        self.client.on_message = self.on_message  # sets the function called when the bridge receives a message
        self.pub_reg_thread = threading.Thread(target=self._pub_reg_loop, daemon=True)
        self.pub_reg_thread.start()

    def _random_device_payload(self):
        # Map these keys to the device JSON format defined in Catalog.py
        device_types = ["temperature_sensor", "humidity_sensor", "motion_sensor", "light_sensor", "switch"]
        rooms = ["kitchen", "living_room", "bedroom", "bathroom", "garage"]

        device_type = random.choice(device_types)
        room = random.choice(rooms)

        return {
            "id": self.clientID,
            "name": f"{device_type}_{self.clientID}",
            "type": device_type,
            "location": room,
            "status": random.choice(["online", "offline"]),
            "value": round(random.uniform(0, 100), 2)
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
                    print("[Device MQTT client] Query all devices not implemented yet")

                case "3":
                    device_id = input("Device ID: ").strip()
                    print(f"[Device MQTT client] Query device by ID not implemented yet: {device_id}")

                case "4":
                    print("[Device MQTT client] Exiting menu")

                case _:
                    print("Invalid option")
    
    def _pub_reg_loop(self):
        while True:
            time.sleep(60)
            payload= json.dumps(self._random_device_payload())
            self.client.publish(REGISTRATION_DEVICES_TOPIC, payload)

    def start(self): 
        self.client.connect(self.broker, self.port, keepalive=60) 
        self.client.loop_start() 
    
    def on_connect(self, client, userdata, flags, rc): #as said, it will handles the action when the bridge connect to the broker
        print(f"[Device MQTT client] Connected with result code {rc}")  # prints the connection result

        self.client.subscribe(f"{REGISTRATION_DEVICES_TOPIC}/{self.clientID}", 1)
        print(f"[Device MQTT client] Subscribed to {REGISTRATION_DEVICES_TOPIC}/{self.clientID}")
        
        self.client.subscribe(ACK_DEVICES_TOPIC_BASE, 1)
        print(f"[Device MQTT client] Subscribed to {ACK_DEVICES_TOPIC_BASE}")
