import paho.mqtt.client as PahoMQTT
import json
import requests
import time
from constants import *

DEBUG = True

def debug_print(message):
    if DEBUG:
        print(message)

class MQTTCatalogBridge: # This class will allows that the Catalog to receive registrations through MQTT
    

    def __init__(self, clientID, broker, port, url):
        self.url=url
        self.get_mqtt_broker()
        self.clientID = clientID

        self.client = PahoMQTT.Client(client_id=clientID) 
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

    def get_mqtt_broker(self):
        broker_data=requests.get(f"{self.url}/broker").json()
        print(broker_data)
        self.port=broker_data["port"]  # public broker that we have to use
        self.broker=broker_data["ip"] # port to use to connect to the broker
    """
        ==============
        Callbacks
        ==============

    """
    def on_connect(self, client, userdata, flags, rc): #as said, it will handles the action when the bridge connect to the broker
        debug_print(f"[MQTT Catalog Bridge] Connected with result code {rc}")  # prints the connection result
        self.client.subscribe(REGISTRATION_DEVICES_TOPIC, 0);        debug_print(f"[MQTT Catalog Bridge] Subscribed to {REGISTRATION_DEVICES_TOPIC}")
        self.client.subscribe(REGISTRATION_SERVICES_TOPIC, 0);         debug_print(f"[MQTT Catalog Bridge] Subscribed to {REGISTRATION_SERVICES_TOPIC}")
        self.client.subscribe(QUERY_ALL_DEVICES_TOPIC, 0);        debug_print(f"[MQTT Catalog Bridge] Subscribed to {QUERY_ALL_DEVICES_TOPIC}") 
        self.client.subscribe(REFRESH_DEVICE_TOPIC, 0)
        self.client.subscribe(f"{QUERY_DEVICE_BY_ID_TOPIC_BASE}/+", 0);        debug_print(f"[MQTT Catalog Bridge] Subscribed to {QUERY_DEVICE_BY_ID_TOPIC_BASE}/+") 
        
    def on_message(self, client, userdata, msg):
        # if a client publishes something on the registration topic, the bridge will receive it in msg
        # and the bridge has to register that device or service on the catalog
        print(msg)
        topic = msg.topic

        try:
            payload = json.loads(msg.payload.decode("utf-8")) #the payload has to have the same config of body in Catalog.py
        except json.JSONDecodeError:
            debug_print("[MQTT Catalog Bridge] Invalid JSON received")
            return 
        
        if topic == REGISTRATION_DEVICES_TOPIC:
            self.handle_device_registration(client, payload)

        elif topic == REGISTRATION_SERVICES_TOPIC:
            self.handle_service_registration(client, payload)

        elif topic == QUERY_ALL_DEVICES_TOPIC:
            self.handle_query_all_devices(client, payload)

        elif topic.startswith(f"{QUERY_DEVICE_BY_ID_TOPIC_BASE}/"):
            device_id = topic.split("/")[-1]
            self.handle_query_device_by_id(client, payload, device_id)
        elif topic == REFRESH_DEVICE_TOPIC:
            self.handle_device_refresh(client, payload)

        else:
            debug_print(f"[MQTT Catalog Bridge] Unknown topic: {topic}")


    def handle_device_refresh(self, client, payload):
        #simply responds to put requests, done to refresh device, can work also as post (since the catalog specifications said so)
        device_id = payload.get("id")

        if device_id is None:
            debug_print("[MQTT Catalog Bridge] Service registration without id")
            return
        
        try:
            r = requests.put(f"{self.url}/devices/{device_id}", json=payload, timeout=5)

            if r.status_code in [200, 201]:
                response = {
                    "result": "ok",
                    "message": "deviced refreshed",
                    "id": device_id,
                    "status_code": r.status_code
                }
            else:
                response = {
                    "result": "error",
                    "message": r.text,
                    "id": device_id,
                    "status_code": r.status_code
                }

        except requests.RequestException as e:
            response = {
                "result": "error",
                "message": str(e),
                "id": device_id
            }
        ack_topic = f"{ACK_DEVICES_TOPIC_BASE}/{device_id}"
        client.publish(ack_topic, json.dumps(response))
        
    def handle_device_registration(self, client, payload):
        device_id = payload.get("id")
        #handles post
        if device_id is None:
            debug_print("[MQTT Catalog Bridge] Device registration without id")
            return

        try:
            r = requests.post(f"{self.url}/devices", json=payload, timeout=5)

            if r.status_code in [200, 201]:
                response = {
                    "result": "ok",
                    "message": "device registered or refreshed",
                    "id": device_id,
                    "status_code": r.status_code
                }
            else:
                response = {
                    "result": "error",
                    "message": r.text,
                    "id": device_id,
                    "status_code": r.status_code
                }

        except requests.RequestException as e:
            response = {
                "result": "error",
                "message": str(e),
                "id": device_id
            }
        ack_topic = f"{ACK_DEVICES_TOPIC_BASE}/{device_id}"
        client.publish(ack_topic, json.dumps(response))
        
    def handle_service_registration(self, client, payload):
        service_id = payload.get("id")

        if service_id is None:
            debug_print("[MQTT Catalog Bridge] Service registration without id")
            return
        
        try:
            r = requests.post(f"{self.url}/services", json=payload, timeout=5)

            if r.status_code in [200, 201]:
                response = {
                    "result": "ok",
                    "message": "service registered or refreshed",
                    "id": service_id,
                    "status_code": r.status_code
                }
            else:
                response = {
                    "result": "error",
                    "message": r.text,
                    "id": service_id,
                    "status_code": r.status_code
                }

        except requests.RequestException as e:
            response = {
                "result": "error",
                "message": str(e),
                "id": service_id
            }
        ack_topic = f"{ACK_SERVICES_TOPIC_BASE}/{service_id}"
        client.publish(ack_topic, json.dumps(response))
        
    def handle_query_all_devices(self, client, payload):
        client_id = payload.get("client_id")
        request_id = payload.get("request_id")

        if client_id is None:
            debug_print("[MQTT Catalog Bridge] Query all devices without client_id")
            return

        response_topic = f"{QUERY_RESPONSE_TOPIC_BASE}/{client_id}"

        try:
            r = requests.get(f"{self.url}/devices", timeout=5)

            if r.status_code == 200:
                response = {
                    "result": "ok",
                    "request_id": request_id,
                    "data": r.json()
                }
            else:
                response = {
                    "result": "error",
                    "request_id": request_id,
                    "status_code": r.status_code,
                    "message": r.text
                }

        except requests.RequestException as e:
            response = {
                "result": "error",
                "request_id": request_id,
                "message": str(e)
            }

        client.publish(response_topic, json.dumps(response))

    def handle_query_device_by_id(self, client, payload, device_id):
        client_id = payload.get("client_id")
        request_id = payload.get("request_id")

        if client_id is None:
            debug_print("[MQTT Catalog Bridge] Query device by ID without client_id")
            return

        response_topic = f"{QUERY_RESPONSE_TOPIC_BASE}/{client_id}"

        try:
            r = requests.get(f"{self.url}/devices/{device_id}", timeout=5)

            if r.status_code == 200:
                response = {
                    "result": "ok",
                    "request_id": request_id,
                    "device_id": device_id,
                    "data": r.json()
                }
            else:
                response = {
                    "result": "error",
                    "request_id": request_id,
                    "device_id": device_id,
                    "status_code": r.status_code,
                    "message": r.text
                }

        except requests.RequestException as e:
            response = {
                "result": "error",
                "request_id": request_id,
                "device_id": device_id,
                "message": str(e)
            }

        client.publish(response_topic, json.dumps(response))


 #for testing
if __name__ == '__main__':

    mqtt_bridge = MQTTCatalogBridge("catalog_bridge_group1", BROKER, PORT, CATALOG_URL)  # Creates the MQTT bridge connected to the same Catalog
    mqtt_bridge.start()  # Starts the MQTT bridge in background

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        mqtt_bridge.stop()
