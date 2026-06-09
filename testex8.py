import time
from DeviceMQTTClient import DeviceMQTTClient
from constants import *

if __name__ == "__main__":
    # Standard client deployment variables
    # (Pointing directly to your working public sandbox broker)
    BROKER_HOST = "test.mosquitto.org"
    BROKER_PORT = 1883
    UNIQUE_ID   = "smart_sensor_kitchen"

    print(f"[CLIENT TEST] Launching Device Client: {UNIQUE_ID}")
    print(f"[CLIENT TEST] Connecting to Target Broker: {BROKER_HOST}:{BROKER_PORT}")

    # Instantiating matching your exact fixed signature layout
    device = DeviceMQTTClient(clientID=UNIQUE_ID, broker=BROKER_HOST, port=BROKER_PORT)
    device.start()

    # Keep main runtime wrapper block responsive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[CLIENT TEST] Terminating local client environment.")