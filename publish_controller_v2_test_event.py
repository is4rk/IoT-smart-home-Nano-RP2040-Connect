import json
import sys
import time

import paho.mqtt.client as PahoMQTT

from constants import BROKER, PORT


def publish(topic, payload):
    client = PahoMQTT.Client(client_id=f"controller_v2_test_pub_{int(time.time())}")
    client.connect(BROKER, PORT, keepalive=60)
    client.loop_start()
    client.publish(topic, json.dumps(payload), qos=0)
    time.sleep(1)
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    room = sys.argv[1] if len(sys.argv) > 1 else "kitchen"
    event_type = sys.argv[2] if len(sys.argv) > 2 else "temperature"
    raw_value = sys.argv[3] if len(sys.argv) > 3 else "27"

    if event_type in ("presence", "motion", "noise"):
        value = raw_value.lower() in ("1", "true", "yes", "on")
        event = {"n": event_type, "u": "boolean", "bv": value}
    else:
        value = float(raw_value)
        event = {"n": "temperature", "u": "Celsius", "v": value}
        event_type = "temperature"

    topic = f"tiot/group1/{room}/{event_type}"
    payload = {
        "bn": f"/sensor/{room}",
        "bt": time.time(),
        "e": [event]
    }
    publish(topic, payload)
    print(f"Published on {topic}: {payload}")
