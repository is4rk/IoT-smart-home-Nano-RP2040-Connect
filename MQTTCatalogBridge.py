import paho.mqtt.client as PahoMQTT
import json
import time
import cherrypy
import threading
import Catalog

BROKER      = "iot.eclipse.org" # public broker that we have to use
PORT        = 1883 # port to use to connect to the broker
GROUP       = "group1" # group ID nececcary to distinguish the path among other groups (because of the broker is public)
BASE_TOPIC = f"/tiot/{GROUP}"
REGISTRATION_TOPIC = f"{BASE_TOPIC}/catalog/registration"  # Topic where devices/services publish their registrations; the bridge will subscribe to it and will handles the communication with the catalog
ACK_TOPIC_BASE = f"{BASE_TOPIC}/catalog/ack"  # As required, the bridge has to send an ACK to the specific device after registration 

class MQTTCatalogBridge: # This class will allows that the Catalog to receive registrations through MQTT
    
    def __init__(self, catalog):
        self.catalog = catalog  # so the bridge can update catalog.json

        self.client = mqtt.Client(client_id=f"catalog_bridge_{GROUP}")  # initialize the MQTT client for the Catalog Bridge.

        self.client.on_connect = self.on_connect  # sets the function called when the bridge connects to the broker
        self.client.on_message = self.on_message  # sets the function called when the bridge receives a message

    """
        ==============
        Loop Settings
        ==============

    """
   
    def _mqtt_loop(self): # Initialize a loop is needed because  MQTT clients must continuously process datas
        self.client.connect(BROKER, PORT, keepalive=60)  # it connects the bridge to the MQTT broker
        self.client.loop_forever()  # Keeps the MQTT client alive and listening for messages
        #TODO FORSE DOVREI USARE UN LOOP START E STOP MA NON HO CAPITO COME

    def start(self):
        threading.Thread(target=self._mqtt_loop, daemon=True).start()  # starts the MQTT loop in a background thread

    """
        ==============
        Callbacks
        ==============

    """
    def on_connect(self, client, userdata, flags, rc): #as said, it will handles the action when the bridge connect to the broker
        print(f"[MQTT Catalog Bridge] Connected with result code {rc}")  # prints the connection result

        client.subscribe(REGISTRATION_TOPIC)  # subscribes to the registration topic

        print(f"[MQTT Catalog Bridge] Subscribed to {REGISTRATION_TOPIC}")
    
    
    def on_message(self, client, userdata, msg):
        # if a client publishes something on the registration topic, the bridge will receive it in msg
        # and the bridge has to register that device or service on the catalog

        body = json.loads(cherrypy.request.body.read()) # it reads the body (body structure in Catalog.py)

        elementType = "devices" if body["type"]=="device" else "services" # It check if it is a device or a service

        body["element"]["time"]=time.time() # update the time

        with self.lock:
            with open(self.json_file_name, "r") as f: # it loads on data the content of catalog.json
                data = json.load(f)
            data[elementType][body["element"]["id"]]=body # then update the id of the device or service
            with open(self.json_file_name, "w") as f:
                json.dump(data, f) # upload the modified catalog

        #after the update, it will send the ack

        ack_topic = f"{ACK_TOPIC_BASE}/{elementType}/{body["element"]["id"]}" # set the topic with the correct id, something like "/tiot/group1/ack/service/0
        client.publish(ack_topic, json.dumps({"result": "ok"}))
        
        # TODO: come gestire gli errori eventuali

if __name__ == '__main__':
    catalog = Catalog()

    mqtt_bridge = MQTTCatalogBridge(catalog)  # Creates the MQTT bridge connected to the same Catalog.
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

    cherrypy.engine.start()
    cherrypy.engine.block()