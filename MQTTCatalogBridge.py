import paho.mqtt.client as PahoMQTT
import json
import requests
import time


BROKER      = "iot.eclipse.org" # public broker that we have to use
PORT        = 1883 # port to use to connect to the broker
GROUP       = "group1" # group ID nececcary to distinguish the path among other groups (because of the broker is public)
BASE_TOPIC = f"/tiot/{GROUP}"
REGISTRATION_DEVICES_TOPIC = f"{BASE_TOPIC}/catalog/devices/registration"  # Topic where devices publish their registrations; the bridge will subscribe to it and will handles the communication with the catalog
REGISTRATION_SERVICES_TOPIC = f"{BASE_TOPIC}/catalog/services/registration"
ACK_DEVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/ack"  # As required, the bridge has to send an ACK to the specific device after registration 
ACK_SERVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/services/ack" 

class MQTTCatalogBridge: # This class will allows that the Catalog to receive registrations through MQTT
    

    def __init__(self, clientID, broker, port):
        self.broker   = broker
        self.port     = port
        self.clientID = clientID

        self.client = PahoMQTT.Client(clientID) 
        self.client.on_connect = self.on_connect  # sets the function called when the bridge connects to the broker
        self.client.on_message = self.on_message  # sets the function called when the bridge receives a message


        

    """
        ==============
        Loop Settings
        ==============

    """
   
    def start(self): # Initialize a loop is needed because  MQTT clients must continuously process datas
        self.client.connect(self.broker, self.port, keepalive=60)  # it connects the bridge to the MQTT broker
        self.client.loop_start()  # Keeps the MQTT client alive and listening for messages
        
    def stop(self):
        self.client.unsubscribe(REGISTRATION_DEVICES_TOPIC)
        self.client.unsubscribe(REGISTRATION_SERVICES_TOPIC)
        self.client.loop_stop()
        self.client.disconnect()

    """
        ==============
        Callbacks
        ==============

    """
    def on_connect(self, client, userdata, flags, rc): #as said, it will handles the action when the bridge connect to the broker
        print(f"[MQTT Catalog Bridge] Connected with result code {rc}")  # prints the connection result

        self.client.subscribe(REGISTRATION_DEVICES_TOPIC, 1)
        print(f"[MQTT Catalog Bridge] Subscribed to {REGISTRATION_DEVICES_TOPIC}")
        
        self.client.subscribe(REGISTRATION_SERVICES_TOPIC, 1)
        print(f"[MQTT Catalog Bridge] Subscribed to {REGISTRATION_SERVICES_TOPIC}")
    
    
    def on_message(self, client, userdata, msg):
        # if a client publishes something on the registration topic, the bridge will receive it in msg
        # and the bridge has to register that device or service on the catalog
        topic = msg.topic
        payload = msg.payload.decode("utf-8") #as a string
        payload = json.loads(payload) #as a JSON; the payload has to have the same config of body in Catalog.py
        id = payload["id"]
        if "devices" in topic:
            r = requests.post("http://localhost:9090/devices", json= payload) 
            ack_topic = f"{ACK_DEVICES_TOPIC_BASE}/{id}" 
            
        else:
            r = requests.post("http://localhost:9090/services", json=payload)
            ack_topic = f"{ACK_SERVICES_TOPIC_BASE}/{id}" 
        
        if r.status_code in [200, 201]:
            client.publish(ack_topic, json.dumps({"result": "ok"})) 
        else:
            client.publish(ack_topic, json.dumps({"result": "error"}))
        
        
if __name__ == '__main__':

    mqtt_bridge = MQTTCatalogBridge("catalog_bridge_group1", BROKER, PORT)  # Creates the MQTT bridge connected to the same Catalog
    mqtt_bridge.start()  # Starts the MQTT bridge in background

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mqtt_bridge.stop()
