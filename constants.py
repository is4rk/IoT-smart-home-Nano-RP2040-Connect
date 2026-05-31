HOST_NAME = "0.0.0.0"
PORT_NUMBER = 9966
rooms = ["living_room", "kitchen", "bedroom"]
sensors = ["temperature", "humidity", "motion"]
units = ["Celsius", "%RH", "bool"]
actuators = ["thermostat", "lights", "blinds"]
SENMLdatas = ["bt" , "bn", "e"]
eDatas = ["n", "u", "v", "bv"]
GROUP = "group1"
CATALOG_URL = "http://localhost:8080/catalog"

# TOPICS

BASE_TOPIC=f"/tiot/{GROUP}"
REGISTRATION_DEVICES_TOPIC = f"{BASE_TOPIC}/catalog/devices/registration"  # Topic where devices publish their registrations; the bridge will subscribe to it and will handles the communication with the catalog
REGISTRATION_SERVICES_TOPIC = f"{BASE_TOPIC}/catalog/services/registration"
ACK_DEVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/ack"  # As required, the bridge has to send an ACK to the specific device after registration 
ACK_SERVICES_TOPIC_BASE = f"{BASE_TOPIC}/catalog/services/ack" 
QUERY_ALL_DEVICES_TOPIC = f"{BASE_TOPIC}/catalog/devices/query" #needed to ask for all registred devices
QUERY_DEVICE_BY_ID_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/query" #for ID research, an ID will be added
QUERY_RESPONSE_TOPIC_BASE = f"{BASE_TOPIC}/catalog/devices/query/response" #also here, an ID will be added
SENSOR_CONFIGURATION_BASE = f"{BASE_TOPIC}/configuration" #topic where the bridge will send the configuration to the sensor, an ID will be added at the end 
