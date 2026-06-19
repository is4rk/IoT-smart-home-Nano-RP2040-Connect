import json
import time
import threading
import requests
import paho.mqtt.client as PahoMQTT

import constants
from CatalogClient import CatalogClient


DEBUG = True

#TODO registrarsi al catalog

def debug_print(message):
    if DEBUG:
        print(message)


class MQTTActuatorBridge: #Receives through MQTT some commands by CommandPublisher on ACTUATOR_COMMAND_TOPIC
   
    def __init__( self, clientID="actuator_bridge", catalog_url=None, rest_base_url="http://localhost:8081"):
        self.clientID = clientID

        self.catalog_url =constants.CATALOG_URL
        self.catalogCli = CatalogClient(self.catalog_url)
        self.actuatorsService_url ="http://localhost:8081/sensor"
        self.feedback_topic = constants.ACTUATOR_FEEDBACK_TOPIC
        self.rest_base_url = rest_base_url

        # get broker infos
        self.broker = self.catalogCli.get_broker()["ip"]
        self.port = int(self.catalogCli.get_broker()["port"])

        self.rooms = constants.rooms
        self.actuators = constants.actuators

        self.running = False #useful for the threads

        self.client = PahoMQTT.Client(self.clientID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        #1. connects to the broker
        self.client.connect(self.broker, self.port, keepalive=60)  # it connects the bridge to the MQTT broker
        self.client.loop_start()  # Keeps the MQTT client alive and listening for messages

        #2. subscribe to commandTopic to read commands from publisher and registration on catalog
        self.client.subscribe(constants.ACTUATOR_COMMAND_TOPIC, 0);        debug_print(f"[MQTT Actuator Bridge] Subscribed to {constants.ACTUATOR_COMMAND_TOPIC}")
        payload = {
            "id": self.clientID,
            "description": "MQTT-REST bridge for smart home actuators",
            "endpoint": self.actuatorsService_url,
            "mqtt": {
                "ip": self.broker,
                "port": self.port,
                "pub_topics": [
                    self.feedback_topic
                ],
                "sub_topics": [
                    constants.ACTUATOR_COMMAND_TOPIC
                ]
            },
            "resources": [
                {
                    "room": room,
                    "target": actuator,
                    "path": f"/sensor/{room}/{actuator}",
                    "method": "POST"
                }
                for room in self.rooms
                for actuator in self.actuators
            ],
            "time": time.time()
        }
        self.catalogCli.register_service(payload)

        #3. a parallel thread is needed to refresh the service until disconnection
        self.running = True
        refresh_thread = threading.Thread(
            target=self.loopRefresh,
            daemon=True
        )
        refresh_thread.start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            debug_print("[MQTTActuatorBridge] Connected to MQTT broker.")
    
    def on_message(self, client, userdata, msg): #it handles the command in JSON from the command publisher

        debug_print(f"\n[MQTTActuatorBridge] Message received on {msg.topic}")

        try:
            command = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            feedback = {
                "result": "error",
                "message": "Invalid JSON received",
                "timestamp": time.time()
            }

            self.publish_feedback(feedback, self.feedback_topic) #send an error message to publisher 
            return

        feedback = self.handle_command(command)

        reply_to = command.get("reply_to", self.feedback_topic)

        self.publish_feedback(feedback, reply_to)

    def stop(self):
        self.running = False
        self.client.unsubscribe(constants.ACTUATOR_COMMAND_TOPIC)
        self.client.disconnect()

    def loopRefresh(self):
        
        #each 60 sec refreshed in catalog
        while self.running:
            time.sleep(60)
            result = self.catalogCli.refresh_service(self.clientID)

    def handle_command(self, command):
        """
        {
            "command_id": "...",
            "sender": "...",
            "target": "lights" | "thermostat" | "blinds",
            "room": "kitchen" | "living_room" | "bedroom",
            "action": "set",
            "value": ...,
            "timestamp": ...,
            "reply_to": "..."
        }
        """

        command_id = command.get("command_id")
        sender = command.get("sender")
        target = command.get("target")
        room = command.get("room")
        action = command.get("action")
        value = command.get("value")

        
        senml_payload = self.command_to_senml(
            room=room,
            target=target,
            value=value
        )

        rest_response = self.send_to_rest_actuator(
            room=room,
            target=target,
            senml_payload=senml_payload
        )
        
        return {
            "result": "ok",
            "command_id": command_id,
            "sender": sender,
            "target": target,
            "room": room,
            "value": value,
            "timestamp": time.time()
        }


    def command_to_senml(self, room, target, value):
        """
        {
            "bn": "/sensor/<room>",
            "bt": time.time(),
            "e": [
                {
                    "n": "<actuator>",
                    "u": "<unit>",
                    "v" oppure "bv": <value>
                }
            ]
        }
        """

        if target == "lights":
            event = {
                "n": "lights",
                "u": "boolean",
                "bv": value
            }

        elif target == "thermostat":
            event = {
                "n": "thermostat",
                "u": "Celsius",
                "v": value
            }

        elif target == "blinds":
            event = {
                "n": "blinds",
                "u": "%",
                "v": value
            }

        else:
            raise ValueError(f"Unsupported actuator target: {target}")

        return {
            "bn": f"/sensor/{room}",
            "bt": time.time(),
            "e": [
                event
            ]
        }

    def send_to_rest_actuator(self, room, target, senml_payload):
        url = f"{self.rest_base_url}/{room}/{target}"
        response = requests.post( url, json=senml_payload, timeout=5 )
        return response


    def publish_feedback(self, feedback, feedback_topic): #it publish the feedback on the feedback_topic
        self.client.publish(feedback_topic,json.dumps(feedback),qos=0)



