import paho.mqtt.client as PahoMQTT
import json
import requests
import time
import cherrypy
import threading
import Catalog

BROKER      = "iot.eclipse.org" # public broker that we have to use
PORT        = 1883 # port to use to connect to the broker
GROUP       = "group1" # group ID nececcary to distinguish the path among other groups (because of the broker is public)
BASE_TOPIC = f"/tiot/{GROUP}"
REGISTRATION_DEVICES_TOPIC = f"{BASE_TOPIC}/catalog/devices/registration"  # Topic where devices publish their registrations; the bridge will subscribe to it and will handles the communication with the catalog
REGISTRATION_SERVICES_TOPIC = f"{BASE_TOPIC}/catalog/services/registration"
ACK_DEVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/ack"  # As required, the bridge has to send an ACK to the specific device after registration 
ACK_SERVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/services/ack" 

class MQTTCatalogBridge: # This class will allows that the Catalog to receive registrations through MQTT
    

    def __init__(self, clientID, broker, port, notifier):
        self.broker   = broker
        self.port     = port
        self.notifier = notifier
        self.clientID = clientID

        self.client = PahoMQTT.Client(clientID=f"catalog_bridge_{GROUP}") 
        self.client.on_connect = self.on_connect  # sets the function called when the bridge connects to the broker
        self.client.on_message = self.on_message  # sets the function called when the bridge receives a message


        

    """
        ==============
        Loop Settings
        ==============

    """
   
    def start(self): # Initialize a loop is needed because  MQTT clients must continuously process datas
        self.client.connect(BROKER, PORT, keepalive=60)  # it connects the bridge to the MQTT broker
        self.client.loop_start()  # Keeps the MQTT client alive and listening for messages
        
    def stop(self):
        self.client.unsubscribe(REGISTRATION_DEVICES_TOPIC)
        self.client.unsubscribe(REGISTRATION_SERVICES_TOPIC)
        self.client.loop_stop()
        self.client.disconnect()

    def startThread(self):
        threading.Thread(target=self._mqtt_loop, daemon=True).start()  # starts the MQTT loop in a background thread

    """
        ==============
        Callbacks
        ==============

    """
    def on_connect(self, client, userdata, flags, rc): #as said, it will handles the action when the bridge connect to the broker
        print(f"[MQTT Catalog Bridge] Connected with result code {rc}")  # prints the connection result

        self.client.subscribe(REGISTRATION_DEVICES_TOPIC, 0)
        print(f"[MQTT Catalog Bridge] Subscribed to {REGISTRATION_DEVICES_TOPIC}")
        
        self.client.subscribe(REGISTRATION_SERVICES_TOPIC, 0)
        print(f"[MQTT Catalog Bridge] Subscribed to {REGISTRATION_SERVICES_TOPIC}")

        
    
    
    def on_message(self, client, userdata, msg):
        # if a client publishes something on the registration topic, the bridge will receive it in msg
        # and the bridge has to register that device or service on the catalog
        topic = msg.topic
        payload = msg.payload.decode("utf-8") #as a string
        payload = json.loads(payload) #as a JSON; the payload has to have the same config of body in Catalog.py
        id = payload["id"]
        if "devices" in topic:
            r = requests.post("/devices", payload) 
            ack_topic = f"{ACK_DEVICES_TOPIC_BASE}/devices/{id}" 
            client.publish(ack_topic, json.dumps({"result": "ok"}))
        else:
            r = requests.post("/services", payload)
            ack_topic = f"{ACK_SERVICES_TOPIC_BASE}/services/{id}" 
            client.publish(ack_topic, json.dumps({"result": "ok"})) 
        
if __name__ == '__main__':

    mqtt_bridge = MQTTCatalogBridge()  # Creates the MQTT bridge connected to the same Catalog.
    mqtt_bridge.start()  # Starts the MQTT bridge in background.

    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'application/json')]
        }
    }

    cherrypy.tree.mount(catalog, '/', conf)  # it mounts the catalog REST developed 

    cherrypy.config.update({'server.socket_port': 9090})
    # TODO NON SO DOVE METTERE LO SOP
    cherrypy.engine.start()
    cherrypy.engine.block()