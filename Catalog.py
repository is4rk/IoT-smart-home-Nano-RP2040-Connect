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
            with open(self.json_file_name, "w") as f:
                json.dump(data, f)

    def GET(self, *path, **query):
        with self.lock:
            with open(self.json_file_name, "r") as f:
                return json.load(f)

    def POST(self, *path, **query):
        body = json.loads(cherrypy.request.body.read())
        body["time"]=time.time()
        with self.lock:
            with open(self.json_file_name, "r") as f:
                data = json.load(f)
            data["devices"][body["id"]]=body
            with open(self.json_file_name, "w") as f:
                json.dump(data, f)

    def PUT(self, *path, **query):
        body = json.loads(cherrypy.request.body.read())
        body["time"]=time.time()
        id_to_update = body["id"]
        with self.lock:
            with open(self.json_file_name, "r") as f:
                data = json.load(f)
            data["devices"][id_to_update]=body
        
        with open(self.json_file_name, "w") as f:
            json.dump(data, f)

    def DELETE(self, *path, **query): #to finish at home
        body = json.loads(cherrypy.request.body.read())
        id_to_delete = body["id"]
        with self.lock:
            with open(self.json_file_name, "r") as f:
                data = json.load(f)
            del data["devices"][id_to_delete] 
            with open(self.json_file_name, "w") as f:
                json.dump(data, f)



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