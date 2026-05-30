import paho.mqtt.client as PahoMQTT
import threading, time, uuid
import random, json
BROKER      = "iot.eclipse.org" # public broker that we have to use
PORT        = 1883 # port to use to connect to the broker
GROUP       = "group1" # group ID nececcary to distinguish the path among other groups (because of the broker is public)
BASE_TOPIC = f"/tiot/{GROUP}"

REGISTRATION_DEVICES_TOPIC = f"{BASE_TOPIC}/catalog/devices/registration" 
REGISTRATION_SERVICES_TOPIC = f"{BASE_TOPIC}/catalog/services/registration"
ACK_DEVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/ack" 
ACK_SERVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/services/ack" 
QUERY_ALL_DEVICES_TOPIC = f"{BASE_TOPIC}/catalog/devices/query"
QUERY_DEVICE_BY_ID_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/query" 
QUERY_RESPONSE_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/query/response"

class DeviceMQTTClient:
    def __init__(self, clientID, broker, port):
        #TODO remeber that broker is no longer universal, maybe make utils file
        self.broker   = broker
        self.port     = port
        self.clientID = clientID
        self.client = PahoMQTT.Client(clientID) 
        self.client.on_connect = self.on_connect  # sets the function called when the bridge connects to the broker
        self.client.on_message = self.on_message  # sets the function called when the bridge receives a message
        self.pub_reg_thread = threading.Thread(target=self._pub_reg_loop, daemon=True)
        self.pub_reg_thread.start()
        self.last_response=None

    def _random_device_payload(self):
        # Map these keys to the device JSON format defined in Catalog.py
        device_types = ["temperature_sensor", "humidity_sensor", "motion_sensor", "light_sensor", "switch", "smart_toilet"]
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
            time.sleep(60)
            payload= json.dumps(self._random_device_payload())
            self.client.publish(REGISTRATION_DEVICES_TOPIC, payload)

    def start(self): 
        self.client.connect(self.broker, self.port, keepalive=60) 
        self.client.loop_start() 
        threading.Thread(target=self._menu_loop, daemon=True).start()
    
    def on_connect(self, client, userdata, flags, rc): #as said, it will handles the action when the bridge connect to the broker
        print(f"[Device MQTT client] Connected with result code {rc}")  # prints the connection result

        self.client.subscribe(f"{ACK_DEVICES_TOPIC_BASE}/{self.clientID}", 0)
        print(f"[Device MQTT client] Subscribed to {ACK_DEVICES_TOPIC_BASE}/{self.clientID}")
        
        self.client.subscribe(f"{QUERY_RESPONSE_TOPIC_BASE}/{self.clientID}", 0)
        print(f"[Device MQTT client] Subscribed to {QUERY_RESPONSE_TOPIC_BASE}/{self.clientID}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            print(f"[Device MQTT client] Received on {msg.topic}: {payload}")
            self.last_response = payload
        except json.JSONDecodeError:
            print("[Device MQTT client] Invalid JSON received")

if __name__ == "__main__":
    device = DeviceMQTTClient("device_001", BROKER, PORT)
    device.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Device MQTT client] Exiting")