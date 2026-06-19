import json
import time
import threading
import requests
import paho.mqtt.client as PahoMQTT

import constants
from CatalogClient import CatalogClient

DEBUG = True

def debug_print(message):
    if DEBUG:
        print(message)


class MQTTActuatorBridge:
   
    def __init__(self, clientID="actuator_bridge", rest_base_url="http://localhost:8081/sensor"):
        self.clientID = clientID
        self.catalog_url = constants.CATALOG_URL
        self.catalogCli = CatalogClient(self.catalog_url)
        self.rest_base_url = rest_base_url
        self.feedback_topic = constants.ACTUATOR_FEEDBACK_TOPIC

        # get broker infos
        broker_info = self.catalogCli.get_broker()
        self.broker = broker_info["ip"]
        self.port = int(broker_info["port"])

        self.rooms = constants.rooms
        self.actuators = constants.actuators
        self.running = False 

        self.client = PahoMQTT.Client(client_id=self.clientID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        self.client.connect(self.broker, self.port, keepalive=60) 
        self.client.loop_start()  

        self.client.subscribe(constants.ACTUATOR_COMMAND_TOPIC, 0)
        debug_print(f"[MQTT Actuator Bridge] Subscribed to {constants.ACTUATOR_COMMAND_TOPIC}")
        
        self.service_payload = {
            "id": self.clientID,
            "description": "MQTT-REST bridge for smart home actuators",
            "endpoint": self.rest_base_url,
            "mqtt": {
                "ip": self.broker,
                "port": self.port,
                "pub_topics": [self.feedback_topic],
                "sub_topics": [constants.ACTUATOR_COMMAND_TOPIC]
            },
            "resources": [
                {
                    "room": room,
                    "target": actuator,
                    "path": f"{self.rest_base_url}/{room}/{actuator}",
                    "method": "POST"
                }
                for room in self.rooms
                for actuator in self.actuators
            ],
            "time": time.time()
        }
        
        try:
            self.catalogCli.register_service(self.service_payload)
        except Exception as e:
            debug_print(f"Initial registration failed: {e}")

        self.running = True
        refresh_thread = threading.Thread(target=self.loopRefresh, daemon=True)
        refresh_thread.start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            debug_print("[MQTTActuatorBridge] Connected to MQTT broker.")
    
    def on_message(self, client, userdata, msg): 
        debug_print(f"\n[MQTTActuatorBridge] Message received on {msg.topic}")

        try:
            command = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            self.publish_feedback({"result": "error", "message": "Invalid JSON"}, self.feedback_topic) 
            return

        feedback = self.handle_command(command)
        self.publish_feedback(feedback, self.feedback_topic)

    def stop(self):
        self.running = False
        self.client.unsubscribe(constants.ACTUATOR_COMMAND_TOPIC)
        self.client.disconnect()

    def loopRefresh(self):
        while self.running:
            time.sleep(60)
            self.service_payload["time"] = time.time()
            try:
                self.catalogCli.refresh_service(self.clientID, self.service_payload)
            except:
                self.catalogCli.register_service(self.service_payload)

    def handle_command(self, command):
        try:
            event = command.get("e", [{}])[0]
            resource_name = event.get("n", "")
            
            parts = resource_name.split("/")
            if len(parts) >= 3:
                room = parts[0]
                target = parts[1]
            else:
                return {"result": "error", "message": "Malformed resource name"}
                
            value = event.get("v") if "v" in event else event.get("bv")
            senml_payload = self.command_to_senml(room, target, value)
            self.send_to_rest_actuator(room, target, senml_payload)
            
            return {
                "result": "ok",
                "target": target,
                "room": room,
                "value": value,
                "timestamp": time.time()
            }
        except Exception as e:
            return {"result": "error", "message": str(e), "timestamp": time.time()}

    def command_to_senml(self, room, target, value):
        if target == "lights":
            event = {
                "n": "lights",
                "u": "boolean",
                "bv": bool(int(value))
            }
        elif target == "thermostat":
            event = {
                "n": "thermostat",
                "u": "Celsius",
                "v": float(value)
            }
        elif target == "blinds":
            event = {
                "n": "blinds",
                "u": "% position",
                "v": int(value)
            }
        else:
            raise ValueError(f"Unsupported actuator target: {target}")

        return {
            "bn": f"/sensor/{room}",
            "bt": time.time(),
            "e": [event]
        }

    def send_to_rest_actuator(self, room, target, senml_payload):
        url = f"{self.rest_base_url}/{room}/{target}"
        response = requests.post(url, json=senml_payload, timeout=5)
        response.raise_for_status()
        return response

    def publish_feedback(self, feedback, feedback_topic):
        self.client.publish(feedback_topic, json.dumps(feedback), qos=0)

if __name__ == '__main__':
    bridge = MQTTActuatorBridge()
    try:
        bridge.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop()
