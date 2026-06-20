#exercise 14 lab 3
import json
import statistics
import threading
import time
from collections import defaultdict, deque

import paho.mqtt.client as PahoMQTT

from CatalogClient import CatalogClient
from constants import BASE_TOPIC, BROKER, CATALOG_URL, PORT


CONFIG_FILE = "smart_home_controller_v2_config.json"

# lab sw3, for the control managment 

class SmartHomeControllerV2:
    def __init__(self, config_file=CONFIG_FILE):
        # it initializes the controller v2 state and loads the rule parameters
        with open(config_file, "r") as f:
            self.config = json.load(f)

        self.client_id = self.config["controller_id"]
        self.catalog = CatalogClient(CATALOG_URL)
        self.broker = BROKER
        self.port = PORT
        self.running = False

        self.temperature_windows = defaultdict(
            lambda: deque(maxlen=int(self.config["stats_window_size"]))
        )
        self.presence_state = defaultdict(lambda: bool(self.config["default_presence"]))
        self.noise_state = defaultdict(lambda: False)
        self.last_temperature = {}

        # fallback topics are used before the catalog starts to discover the real actuators
        self.command_topics = {
            name: {topic}
            for name, topic in self.config["fallback_command_topics"].items()
        }
        self.subscribed_topics = set()

        self.client = PahoMQTT.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def start(self):
        # starts catalog discovery, service registration and the MQTT client
        broker_info = self.catalog.get_broker()
        self.broker = broker_info.get("ip", self.broker)
        self.port = int(broker_info.get("port", self.port))

        self.refresh_catalog_topics()
        self.register_service()

        self.running = True
        threading.Thread(target=self.registration_loop, daemon=True).start()
        threading.Thread(target=self.catalog_poll_loop, daemon=True).start()

        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

    def stop(self):
        # it stops the background MQTT loop and  disconnects the client
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()

    def register_service(self):
        # this registers or  refreshes this controller as a catalog service
        payload = self.build_service_payload()
        try:
            self.catalog.register_service(payload)
        except Exception:
            self.catalog.refresh_service(self.client_id, payload)

    def build_service_payload(self):
        # builds the catalog profile describing the controller
        pub_topics = sorted({topic for topics in self.command_topics.values() for topic in topics})
        pub_topics.append(f"{self.config['alert_topic_base']}/+/temperature")
        return {
            "id": self.client_id,
            "description": "Integrated Smart Home Controller v2 for exercise 14",
            "endpoint": None,
            "mqtt": {
                "ip": self.broker,
                "port": self.port,
                "pub_topics": pub_topics,
                "sub_topics": sorted(self.subscribed_topics) or [f"{BASE_TOPIC}/+/temperature"]
            },
            "resources": [
                "remote_temperature_policy",
                "remote_presence_fusion",
                "fan_control",
                "heater_control",
                "lcd_message_control",
                "temperature_alerts"
            ],
            "time": time.time()
        }

    def registration_loop(self):
        # keeps the service alive in the catalog by refreshing it periodically
        while self.running:
            time.sleep(float(self.config["registration_refresh_seconds"]))
            try:
                self.catalog.refresh_service(self.client_id, self.build_service_payload())
            except Exception as e:
                print(f"[Controller14] Catalog refresh failed: {e}")

    def catalog_poll_loop(self):
        # checks the catalog again from to find new devices
        while self.running:
            time.sleep(float(self.config["catalog_poll_seconds"]))
            self.refresh_catalog_topics()

    def refresh_catalog_topics(self):
        # it discovers sensor topics and actuator command topics from the catalog
        try:
            devices = self.catalog.get_devices()
        except Exception as e:
            print(f"[Controller14] Could not read Catalog devices: {e}")
            return

        if isinstance(devices, dict):
            devices = list(devices.values())

        for device in devices or []:
            mqtt = device.get("mqtt", {})
            # sensor publications are subscribed so the controller can receive events
            for topic in mqtt.get("pub_topics", []):
                if any(word in topic for word in ("temperature", "presence", "motion", "noise")):
                    self.subscribe(topic)

            # actuator subscription topics become command topics for this controller
            for topic in mqtt.get("sub_topics", []):
                lowered = topic.lower()
                if "led" in lowered:
                    self.command_topics.setdefault("led", set()).add(topic)
                elif "fan" in lowered:
                    self.command_topics.setdefault("fan", set()).add(topic)
                elif "heater" in lowered:
                    self.command_topics.setdefault("heater", set()).add(topic)
                elif "lcd" in lowered:
                    self.command_topics.setdefault("lcd", set()).add(topic)

        for sensor in ("temperature", "presence", "motion", "noise"):
            self.subscribe(f"{BASE_TOPIC}/+/{sensor}")

    def subscribe(self, topic):
        # it adds one topic to the subscription set, avoiding duplicates
        if topic in self.subscribed_topics:
            return
        self.subscribed_topics.add(topic)
        if self.client.is_connected():
            self.client.subscribe(topic, qos=0)
        print(f"[Controller14] Subscribed to {topic}")

    def on_connect(self, client, userdata, flags, rc):
        # subscribes again after connection because subscriptions may be lost
        print(f"[Controller14] Connected to MQTT broker with rc={rc}")
        for topic in self.subscribed_topics:
            self.client.subscribe(topic, qos=0)

    def on_message(self, client, userdata, msg):
        # make MQTT messages as JSON and handles the SenML record
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            print(f"[Controller14] Ignoring non-JSON payload on {msg.topic}")
            return

        records = payload if isinstance(payload, list) else [payload]
        for record in records:
            self.handle_senml_record(msg.topic, record)

    def handle_senml_record(self, topic, record):
        # it address each SenML event to the correct handler
        if not isinstance(record, dict) or "e" not in record:
            return

        room = self.room_from_record(topic, record)
        for event in record.get("e", []):
            name = event.get("n")
            if name == "temperature" and "v" in event:
                self.handle_temperature(room, float(event["v"]))
            elif name in ("presence", "motion"):
                self.handle_presence(room, bool(event.get("bv", event.get("v", False))))
            elif name == "noise":
                self.handle_noise(room, bool(event.get("bv", event.get("v", False))))

    def room_from_record(self, topic, record):
        # it takes  the rooms from the SenML base name or from the MQTT topic
        bn = str(record.get("bn", ""))
        parts = [part for part in bn.split("/") if part]
        if len(parts) >= 2 and parts[0] == "sensor":
            return parts[1]
        for candidate in ("living_room", "kitchen", "bedroom"):
            if candidate in topic.split("/"):
                return candidate
        return self.config["default_room"]

    def handle_temperature(self, room, value):
        # it  stores the last temperature and updates the  statistics
        self.last_temperature[room] = value
        window = self.temperature_windows[room]
        window.append(value)
        stats = {
            "min": min(window),
            "max": max(window),
            "mean": statistics.fmean(window),
            "count": len(window)
        }
        print(f"[Controller14] {room} temperature={value:.2f} stats={stats}")
        self.apply_remote_policy(room)
        if value > float(self.config["alert_temperature_threshold"]):
            self.publish_alert(room, value, stats)

    def handle_presence(self, room, value):
        # it updates presence, also considering previous noise detections
        self.presence_state[room] = value or self.noise_state[room]
        print(f"[Controller14] {room} presence={self.presence_state[room]}")
        self.apply_remote_policy(room)

    def handle_noise(self, room, value):
        # uses noise as an additional  indicatator that somebody may be present
        self.noise_state[room] = value
        self.presence_state[room] = value or self.presence_state[room]
        print(f"[Controller14] {room} noise={value}")
        self.apply_remote_policy(room)

    def apply_remote_policy(self, room):
        # it  computes actuator commands using temperature and information abotu presenxe
        if room not in self.last_temperature:
            return

        temperature = self.last_temperature[room]
        presence = self.presence_state[room]
        fan_cfg = self.config["fan_presence"] if presence else self.config["fan_no_presence"]
        heater_cfg = self.config["heater_presence"] if presence else self.config["heater_no_presence"]

        fan = self.linear_fan(temperature, fan_cfg["min"], fan_cfg["max"])
        heater = self.linear_heater(temperature, heater_cfg["min"], heater_cfg["max"])
        led = 1 if presence and temperature <= float(self.config["temperature_threshold"]) else 0

        self.publish_command("fan", fan, "PWM")
        self.publish_command("heater", heater, "PWM")
        self.publish_command("led", led, "bool")
        self.publish_lcd(room, temperature, presence, fan, heater)

    def linear_fan(self, temp, tmin, tmax):
        # converts temperature into a fan PWM value between 0 and 255
        if temp <= tmin:
            return 0
        if temp >= tmax:
            return 255
        return int(255.0 * (temp - tmin) / (tmax - tmin))

    def linear_heater(self, temp, tmin, tmax):
        # converts temperature into a heater PWM value between 255 an 0
        if temp <= tmin:
            return 255
        if temp >= tmax:
            return 0
        return int(255.0 * (1.0 - ((temp - tmin) / (tmax - tmin))))

    def publish_command(self, target, value, unit):
        # publishes a command for one actuator type on every known topic
        payload = {
            "bn": self.client_id,
            "e": [
                {
                    "t": int(time.time()),
                    "n": target,
                    "v": value,
                    "u": unit
                }
            ]
        }
        for topic in sorted(self.command_topics.get(target, [])):
            self.client.publish(topic, json.dumps(payload), qos=0)
            print(f"[Controller14] {target}={value} published on {topic}")

    def publish_lcd(self, room, temperature, presence, fan, heater):
        # sends a  status message to the LCD 
        message = f"{room} T:{temperature:.1f} P:{int(presence)} F:{int(fan/255*100)} H:{int(heater/255*100)}"
        payload = {
            "bn": self.client_id,
            "e": [
                {
                    "t": int(time.time()),
                    "n": "lcd",
                    "vs": message,
                    "u": "text"
                }
            ]
        }
        for topic in sorted(self.command_topics.get("lcd", [])):
            self.client.publish(topic, json.dumps(payload), qos=0)
            print(f"[Controller14] LCD message published on {topic}: {message}")

    def publish_alert(self, room, temperature, stats):
        # publishes a temperature alert of current statistics
        topic = f"{self.config['alert_topic_base']}/{room}/temperature"
        payload = {
            "bn": f"/alerts/{room}",
            "bt": time.time(),
            "e": [
                {
                    "n": "temperature_alert",
                    "u": "Celsius",
                    "v": temperature
                }
            ],
            "stats": stats
        }
        self.client.publish(topic, json.dumps(payload), qos=0)
        print(f"[Controller14] Alert published on {topic}: {payload}")

#for testing
if __name__ == "__main__":
    # runs the controller v2 as a standalone script
    controller = SmartHomeControllerV2()
    controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
