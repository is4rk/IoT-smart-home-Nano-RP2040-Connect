import cherrypy
import json
import time
import threading
class Catalog:
    def __init__(self):
        self.lock = threading.Lock()
        self.json_file_name="catalog.json"
        threading.Thread(target=self._cleanup_loop, daemon=True).start()

    def _cleanup_loop(self):
        while True:
            time.sleep(60)
            self._cleanup()
    def _cleanup(self):
        now = time.time()
        with self.lock:
            with open(self.json_file_name, "r") as f:
                data=json.load(f)
            for id, device in list(data["devices"].items()):
                if now - device["time"] > 120:
                    del data["devices"][id]
            for id, service in list(data["services"].items()):
                if now - service["time"] > 120:
                    del data["services"][id]
            with open(self.json_file_name, "w") as f:
                json.dump(data, f)

    def GET(self, *path, **query):
        with self.lock:
            with open(self.json_file_name, "r") as f:
                return json.load(f)

    def POST(self, *path, **query):
        body = json.loads(cherrypy.request.body.read())
        elementType = "devices" if body["type"]==False else "services"
        body["element"]["time"]=time.time()
        with self.lock:
            with open(self.json_file_name, "r") as f:
                data = json.load(f)
            data[elementType][body["id"]]=body
            with open(self.json_file_name, "w") as f:
                json.dump(data, f)

    def PUT(self, *path, **query):
        body = json.loads(cherrypy.request.body.read())
        elementType = "devices" if body["type"]==False else "services"
        body["element"]["time"]=time.time()
        id_to_update = body["element"]["id"]
        with self.lock:
            with open(self.json_file_name, "r") as f:
                data = json.load(f)
            data[elementType][id_to_update]=body
        
        with open(self.json_file_name, "w") as f:
            json.dump(data, f)

    def DELETE(self, *path, **query): #to finish at home
        body = json.loads(cherrypy.request.body.read())
        elementType = "devices" if body["type"]==False else "services"
        id_to_delete = body["element"]["id"]
        with self.lock:
            with open(self.json_file_name, "r") as f:
                data = json.load(f)
            del data[elementType][id_to_delete] 
            with open(self.json_file_name, "w") as f:
                json.dump(data, f)

# body = {
#   "type": bool,
#   "element": {...}
# }


# device = {
#     "id": "device_001",
#     "description": "Living room temperature sensor",
#     "endpoint": "http://localhost:8080/sensor/temperature",
#     "mqtt": {
#         "ip": "iot.eclipse.org",
#         "port": 1883,
#         "topic": "/tiot/group01/temperature"
#     },
#     "resources": ["temperature", "humidity"],
#     "time": time.time()
# }


# services = {
#   "id": "service_001",
#     "description": "Smart home device actuator",
#     "endpoint": "TO DO",
#     "mqtt": {
#         "ip": "iot.eclipse.org",
#         "port": 1883,
#         "topic": "/tiot/group01/smartHome"
#     },
#     "resources": [TO DO],
#     "time": time.time()
# }

# data:
# {
#   "broker": {...},
#   "devices": {
#     "device_001": {...},
#     "device_002": {...}
#   },
#   "services": {
#     "service_001": {...}
#   }
# }