import json
import statistics
import threading
import time
from collections import defaultdict, deque

import paho.mqtt.client as PahoMQTT
import requests

from CatalogClient import CatalogClient
from constants import BASE_TOPIC, BROKER, CATALOG_URL, PORT


CONFIG_FILE = "smart_home_controller_config.json"


class SmartHomeController:
    def __init__(self, config_file=CONFIG_FILE):
        self.config = self._load_config(config_file)
        self.client_id = self.config["controller_id"]
        self.catalog = CatalogClient(CATALOG_URL)

        self.broker = BROKER
        self.port = PORT
        self.running = False

        self.temperature_windows = defaultdict(
            lambda: deque(maxlen=int(self.config["stats_window_size"]))
        )
        self.motion_state = defaultdict(lambda: bool(self.config["default_motion"]))
        self.led_command_topics = set()
        self.subscribed_topics = set()

        self.client = PahoMQTT.Client(client_id=self.client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def _load_config(self, config_file):
        with open(config_file, "r") as f:
            return json.load(f)

    def start(self):
        broker_info = self.catalog.get_broker()
        self.broker = broker_info.get("ip", self.broker)
        self.port = int(broker_info.get("port", self.port))

        self.register_service()
        self.refresh_catalog_topics()

        self.running = True
        threading.Thread(target=self.registration_loop, daemon=True).start()
        threading.Thread(target=self.catalog_poll_loop, daemon=True).start()

        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

    def stop(self):
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()

    def register_service(self):
        payload = self.build_service_payload()
        try:
            self.catalog.register_service(payload)
        except Exception:
            self.catalog.refresh_service(self.client_id, payload)

    def build_service_payload(self):
        return {
            "id": self.client_id,
            "description": "Integrated Smart Home Controller for exercise 13",
            "endpoint": None,
            "mqtt": {
                "ip": self.broker,
                "port": self.port,
                "pub_topics": [
                    self.config["fallback_led_command_topic"],
                    f"{self.config['alert_topic_base']}/+/temperature"
                ],
                "sub_topics": list(self.subscribed_topics) or [f"{BASE_TOPIC}/+/temperature"]
            },
            "resources": [
                "temperature_rule_engine",
                "motion_rule_engine",
                "rolling_temperature_statistics",
                "temperature_alerts",
                "arduino_led_control"
            ],
            "time": time.time()
        }

    def registration_loop(self):
        while self.running:
            time.sleep(float(self.config["registration_refresh_seconds"]))
            try:
                self.catalog.refresh_service(self.client_id, self.build_service_payload())
            except Exception as e:
                print(f"[Controller] Catalog refresh failed: {e}")

    def catalog_poll_loop(self):
        while self.running:
            time.sleep(float(self.config["catalog_poll_seconds"]))
            self.refresh_catalog_topics()

    def refresh_catalog_topics(self):
        try:
            devices = self._catalog_values(self.catalog.get_devices())
        except Exception as e:
            print(f"[Controller] Could not read devices from Catalog: {e}")
            return

        for device in devices:
            mqtt = device.get("mqtt", {})
            for topic in mqtt.get("pub_topics", []):
                if self._is_sensor_topic(topic):
                    self.subscribe(topic)

            for topic in mqtt.get("sub_topics", []):
                if "led" in topic and ("command" in topic or "cmd" in topic):
                    self.led_command_topics.add(topic)

        self.led_command_topics.add(self.config["fallback_led_command_topic"])
        self.subscribe(f"{BASE_TOPIC}/+/temperature")
        self.subscribe(f"{BASE_TOPIC}/+/motion")
        self.subscribe(f"{BASE_TOPIC}/+/sensors/temperature")
        self.subscribe(f"{BASE_TOPIC}/+/sensors/motion")

    def _catalog_values(self, catalog_section):
        if isinstance(catalog_section, dict):
            return list(catalog_section.values())
        return catalog_section or []

    def _is_sensor_topic(self, topic):
        sensor_words = ("temperature", "humidity", "motion")
        return any(word in topic for word in sensor_words)

    def subscribe(self, topic):
        if topic in self.subscribed_topics:
            return
        self.subscribed_topics.add(topic)
        if self.client.is_connected():
            self.client.subscribe(topic, qos=0)
        print(f"[Controller] Subscribed to {topic}")

    def on_connect(self, client, userdata, flags, rc):
        print(f"[Controller] Connected to MQTT broker with rc={rc}")
        for topic in self.subscribed_topics:
            self.client.subscribe(topic, qos=0)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            print(f"[Controller] Ignoring non-JSON payload on {msg.topic}")
            return

        records = payload if isinstance(payload, list) else [payload]
        for record in records:
            self.handle_senml_record(msg.topic, record)

    def handle_senml_record(self, topic, record):
        if not isinstance(record, dict) or "e" not in record:
            return

        room = self.room_from_record(topic, record)
        for event in record.get("e", []):
            name = event.get("n")
            if name == "temperature" and "v" in event:
                self.handle_temperature(room, float(event["v"]))
            elif name == "motion":
                value = event.get("bv", event.get("v", False))
                self.handle_motion(room, bool(value))

    def room_from_record(self, topic, record):
        bn = str(record.get("bn", ""))
        parts = [part for part in bn.split("/") if part]
        if len(parts) >= 2 and parts[0] == "sensor":
            return parts[1]

        topic_parts = topic.split("/")
        for candidate in ("living_room", "kitchen", "bedroom"):
            if candidate in topic_parts:
                return candidate
        return self.config["default_room"]

    def handle_temperature(self, room, value):
        window = self.temperature_windows[room]
        window.append(value)

        stats = {
            "min": min(window),
            "max": max(window),
            "mean": statistics.fmean(window),
            "count": len(window)
        }
        print(f"[Controller] {room} temperature={value:.2f} stats={stats}")

        self.evaluate_rules(room, value)

        if value > float(self.config["alert_temperature_threshold"]):
            self.publish_alert(room, value, stats)

    def handle_motion(self, room, value):
        self.motion_state[room] = value
        print(f"[Controller] {room} motion={value}")
        if not value:
            self.publish_led_command(0)

    def evaluate_rules(self, room, temperature):
        motion = self.motion_state[room]
        threshold = float(self.config["temperature_threshold"])

        if not motion:
            self.publish_led_command(0)
        elif temperature > threshold:
            self.publish_led_command(0)
        else:
            self.publish_led_command(1)

    def publish_led_command(self, value):
        payload = {
            "bn": self.client_id,
            "e": [
                {
                    "t": int(time.time()),
                    "n": "led",
                    "v": int(value),
                    "u": "bool"
                }
            ]
        }
        for topic in sorted(self.led_command_topics):
            self.client.publish(topic, json.dumps(payload), qos=0)
            print(f"[Controller] LED command {value} published on {topic}")

    def publish_alert(self, room, temperature, stats):
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
        print(f"[Controller] Alert published on {topic}: {payload}")


if __name__ == "__main__":
    controller = SmartHomeController()
    controller.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
