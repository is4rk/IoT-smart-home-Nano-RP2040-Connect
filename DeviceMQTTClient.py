import paho.mqtt.client as PahoMQTT

BROKER      = "iot.eclipse.org" # public broker that we have to use
PORT        = 1883 # port to use to connect to the broker
GROUP       = "group1" # group ID nececcary to distinguish the path among other groups (because of the broker is public)
BASE_TOPIC = f"/tiot/{GROUP}"
REGISTRATION_DEVICES_TOPIC = f"{BASE_TOPIC}/catalog/devices/registration"  # Topic where devices publish their registrations; the bridge will subscribe to it and will handles the communication with the catalog
ACK_DEVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/ack"  # As required, the bridge has to send an ACK to the specific device after registration 

class DeviceMQTTClient:
    def __init__(self, clientID, broker, port):
        self.broker   = broker
        self.port     = port
        self.clientID = clientID
        self.client = PahoMQTT.Client(clientID) 
        self.client.on_connect = self.on_connect  # sets the function called when the bridge connects to the broker
        self.client.on_message = self.on_message  # sets the function called when the bridge receives a message
    
    def start(self): 
        self.client.connect(self.broker, self.port, keepalive=60) 
        self.client.loop_start() 
    
    def on_connect(self, client, userdata, flags, rc): #as said, it will handles the action when the bridge connect to the broker
        print(f"[Device MQTT client] Connected with result code {rc}")  # prints the connection result

        self.client.subscribe(REGISTRATION_DEVICES_TOPIC, 1)
        print(f"[Device MQTT client] Subscribed to {REGISTRATION_DEVICES_TOPIC}")
        
        self.client.subscribe(ACK_DEVICES_TOPIC_BASE, 1)
        print(f"[Device MQTT client] Subscribed to {ACK_DEVICES_TOPIC_BASE}")
