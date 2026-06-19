import uuid

import constants
from CatalogClient import CatalogClient
import paho.mqtt.client as PahoMQTT
import threading
import json
import requests
import time

DEBUG = False

def debug_print(message):
    if DEBUG:
        print(message)


class MQTTActuatorCommandPublisher:

    def __init__(self, clientID, url):
        self.clientID = clientID
        self.client = PahoMQTT.Client(clientID) #ex command_pub_001
        self.url= url

        #getting broker infos using a CataloClient
        self.catalogCli = CatalogClient(url)
        response = self.catalogCli.get_broker()
        metadata = response.json() if hasattr(response, 'json') else response
        self.broker = metadata["ip"]
        self.port = metadata["port"]
        
        self.running = False #useful for the parallel thread

        self.client.on_connect = self.on_connect  # sets the function called when the bridge connects to the broker
        self.client.on_message = self.on_message  # sets the function called when the bridge receives a message        

    def start(self): # Initialize a loop is needed because  MQTT clients must continuously process datas
        # 1. start connection & start loop
        self.client.connect(self.broker, self.port, keepalive=60)  # it connects the bridge to the MQTT broker
        self.client.loop_start()  # Keeps the MQTT client alive and listening for messages

        # 2. As soon as it connects to the broker, asks the catalog for the devices & services list
        arduino_device = None
        actuator_service = None
        
        while not arduino_device or not actuator_service:
            devices = self.catalogCli.get_devices()
            services = self.catalogCli.get_services()
            
            arduino_device = next((d for d in devices if "arduino" in d["id"]), None)
            actuator_service = next((s for s in services if "actuator_service" in s["id"]), None)
            
            if not arduino_device or not actuator_service:
                print("Waiting for Arduino and Actuator Service to register...")
                time.sleep(5)

        # 3. define feedback and command topics
        ARDUINO_LED_COMMAND_TOPIC = next(
            topic for topic in arduino_device["sub_topics"]
            if "command" in topic
        )  # command publisher will pub on it

        ARDUINO_LED_FEEDBACK_TOPIC = next(
            topic for topic in arduino_device["pub_topics"]
            if "feedback" in topic
        ) # command publisher will sub on it

        ACTUATOR_COMMAND_TOPIC = next(
            topic for topic in actuator_service["sub_topics"]
            if "command" in topic
        )  # command publisher will pub on it

        ACTUATOR_FEEDBACK_TOPIC = next(
            topic for topic in actuator_service["pub_topics"]
            if "feedback" in topic
        ) # command publisher will sub on it, will be something like tiot/group1/.../feedback

        # 4. subscribe to feedback topics
        self.client.subscribe(ARDUINO_LED_FEEDBACK_TOPIC, 0);        debug_print(f"[MQTT Command Publisher] Subscribed to {ARDUINO_LED_FEEDBACK_TOPIC}")
        self.client.subscribe(ACTUATOR_FEEDBACK_TOPIC, 0);        debug_print(f"[MQTT Command Publisher] Subscribed to {ACTUATOR_FEEDBACK_TOPIC}")

        # 5. initialize a parallel thread to refresh the service
        self.running = True
        refresh_thread = threading.Thread( #you can not save the variable to the class, casue its a Daemon thread and cause the threading module keeps track of it
            target=self.loopRefresh,
            args=(
                ARDUINO_LED_COMMAND_TOPIC,
                ACTUATOR_COMMAND_TOPIC,
                ARDUINO_LED_FEEDBACK_TOPIC,
                ACTUATOR_FEEDBACK_TOPIC
            ),
            daemon=True
        )
        
        refresh_thread.start()

        #6. start the loop to ask commands
        self.commandLineLoop(self, ARDUINO_LED_COMMAND_TOPIC, ACTUATOR_COMMAND_TOPIC, ARDUINO_LED_FEEDBACK_TOPIC, ACTUATOR_FEEDBACK_TOPIC)

        #7. stop
        self.stop(ARDUINO_LED_FEEDBACK_TOPIC, ACTUATOR_FEEDBACK_TOPIC)


    def on_connect(self, client, userdata, flags, rc): #as said, it will handles the action when the bridge connect to the broker
        debug_print(f"[MQTT command Publisher ] Connected with result code {rc}")  # prints the connection result

        


        
    def stop(self, feedbackTopicArduino, feedbackTopicActuator):
        self.client.unsubscribe(feedbackTopicArduino)
        self.client.unsubscribe(feedbackTopicActuator)
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        
    def commandLineLoop(self, commandTopicArduino, commandTopicActuator, feedbackTopicArduino, feedbackTopicActuator):

        print(" CLI del Command Publisher. " \
        "\nComandi supportati:" \
        "\n* led <0|1>" \
        "\n* lights <room> <0|1>" \
        "\n* thermostat <room> <value>" \
        "\n* blinds <room> <0-100>" \
        "\n* Q to quit\n")
       
        
        while True:
            deviceType = input("Actuator or Arduino? ").strip().lower()

            if deviceType == "q":
                print("Exiting Command Publisher CLI.")
                break

            elif deviceType == "actuator":
                line = input("Insert valid Actuator Command:\n").strip()

                if line.upper() == "Q":
                    print("Exiting Command Publisher CLI.")
                    break

                parts = line.split()

                if len(parts) == 0:
                    print("Invalid command: empty command.\n")
                    continue

                command = parts[0].lower()

                # =========================
                # LIGHTS <room> <0|1>
                # =========================

                if command == "lights":
                    if len(parts) != 3:
                        print("Invalid lights command. Use: lights <room> <0|1>\n")
                        continue

                    room = parts[1]
                    value = parts[2]

                    if room not in constants.rooms: #constants.rooms defined in constants
                        print(f"Invalid room: {room}. Valid constants.rooms: {constants.rooms}\n")
                        continue

    
                    if value not in ["0","1"]:
                        print("Invalid lights value. Use 0 or 1.\n")
                        continue

                    payload = self.buildCommand(
                        target="lights",
                        room=room,
                        value=value,
                        unit= "int"
                    )

                    self.client.publish(commandTopicActuator, json.dumps(payload), qos=0)

                # =========================
                # THERMOSTAT <room> <value>
                # =========================

                elif command == "thermostat":
                    if len(parts) != 3:
                        print("Invalid thermostat command. Use: thermostat <room> <value>\n")
                        continue

                    room = parts[1]
                    rawValue = parts[2]

                    if room not in constants.rooms:
                        print(f"Invalid room: {room}. Valid constants.rooms: {constants.rooms}\n")
                        continue

                    try:
                        value = float(rawValue)
                    except ValueError:
                        print("Invalid thermostat value. Use a numeric value.\n")
                        continue

                    if value < 10 or value > 30:
                        print("Invalid thermostat value. Use a value between 10 and 30 °C.\n")
                        continue

                    payload = self.buildCommand(
                        target="thermostat",
                        room=room,
                        value=value,
                        unit="Cel"
                    )

                    self.client.publish(commandTopicActuator, json.dumps(payload), qos=0)

                # =========================
                # BLINDS <room> <0-100>
                # =========================

                elif command == "blinds":
                    if len(parts) != 3:
                        print("Invalid blinds command. Use: blinds <room> <0-100>\n")
                        continue

                    room = parts[1]
                    rawValue = parts[2]

                    if room not in constants.rooms:
                        print(f"Invalid room: {room}. Valid constants.rooms: {constants.rooms}\n")
                        continue

                    try:
                        value = int(rawValue)
                    except ValueError:
                        print("Invalid blinds value. Use an integer between 0 and 100.\n")
                        continue

                    if value < 0 or value > 100:
                        print("Invalid blinds value. Use a value between 0 and 100.\n")
                        continue

                    payload = self.buildCommand(
                        target="blinds",
                        room=room,
                        value=value,
                        unit = "int"
                    )
                    self.client.publish(commandTopicActuator, json.dumps(payload), qos=0)

                else:
                    print(
                        "Invalid actuator command.\n"
                        "Use one of:\n"
                        "- lights <room> <0|1>\n"
                        "- thermostat <room> <value>\n"
                        "- blinds <room> <0-100>\n"
                    )

            elif deviceType == "arduino":
                line = input("Insert valid Arduino Command:\n").strip()

                if line.upper() == "Q":
                    print("Exiting Command Publisher CLI.")
                    break

                parts = line.split()

                if len(parts) == 0:
                    print("Invalid command: empty command.\n")
                    continue

                command = parts[0].lower()

                # =========================
                # LED <0|1>
                # =========================

                if command == "led":
                    if len(parts) != 2:
                        print("Invalid led command. Use: led <0|1>\n")
                        continue

                    value = parts[1]

                    if value in ["0","1"]:
                        print("Invalid led value. Use 0 or 1.\n")
                        continue

                    payload = self.buildCommand(
                        target="led",
                        value=value,
                        room=None,
                        unit = int
                    )
                    self.client.publish(commandTopicArduino, json.dumps(payload), qos=0)
                    

                else:
                    print(
                        "Invalid Arduino command.\n"
                        "Use:\n"
                        "- led <0|1>\n"
                    )

            else:
                print("Invalid choice. Type Actuator, Arduino, or Q.\n")

    def buildCommand(self, target, value, room=None, unit=""):

        resource_name = f"{room}/{target}/command" if room is not None else f"{target}/command"

        return {
            "bn": self.clientID,
            "e": [
                {
                    "t": int(time.time()),
                    "n": resource_name,
                    "v": value,
                    "u": unit
                }
            ]
        }

        
    def loopRefresh(self, commandTopicArduino, commandTopicActuator, feedbackTopicArduino, feedbackTopicActuator):
        # Periodic refresh of Command Publisher on Catalog.
        while self.running:
            #building the record
            service = {
                "id": self.clientID,
                "type": "command_publisher",
                "description": "Service used to send manual commands to Arduino LED and Smart Home actuators",
                "endpoint": None,
                "mqtt": {
                    "ip": self.broker,
                    "port": self.port,
                    # topic where commands are published
                    "pub_topics": [
                        commandTopicArduino,
                        commandTopicActuator
                    ],

                    # topics where feedback are received
                    "sub_topics": [
                        feedbackTopicArduino, 
                        feedbackTopicActuator
                    ]
                },
                "resources": [
                    "arduino_led_control",
                    "lights_control",
                    "thermostat_control",
                    "blinds_control"
                ],

                "time": time.time()
            }

            try:
                self.catalogCli.refresh_service(self.clientID, service)
            except:
                self.catalogCli.register_service(service)
                
            time.sleep(60)
       
    def on_message(self, client, userdata, msg):
        
        print("\n[MQTT Command Publisher] Feedback received")
        print(f"Topic: {msg.topic}")
        payload = json.loads(msg.payload.decode("utf-8"))
        print(json.dumps(payload))


"""
{
    'bn' : 'ArduinoGroup1'
    'e' : [{
        'n' : 'led'
        't': null
        'v': 1
        'u' null
    }]
}

"""


if __name__ == '__main__':
    # URL matches the one defined in constants.py for the Catalog
    catalog_url = constants.CATALOG_URL
    
    # Initialize and start the publisher
    publisher = MQTTActuatorCommandPublisher("command_publisher_001", catalog_url)
    try:
        publisher.start()
    except KeyboardInterrupt:
        print("\nPublisher manually stopped.")