import cherrypy
import json
import time
import threading
class Catalog:

    def __init__(self):
        self.lock = threading.Lock() # Lock is used to avoid concurrent read/write operations on catalog.json.
        self.json_file_name="catalog.json"
        threading.Thread(target=self._cleanup_loop, daemon=True).start()   # It starts the cleanup thread in background when the Catalog is created.

    def _cleanup_loop(self): # As required, every 60 seconds it clean-up deprecated devices/services
        while True:
            time.sleep(60)
            self._cleanup() # it call the following function _cleanup()
    
    def _cleanup(self):
        now = time.time() # It register in now the current time to check  
        with self.lock:
            with open(self.json_file_name, "r") as f:
                data=json.load(f) #load on data the catalog.json
            for id, device in list(data["devices"].items()): 
                if now - device.get("time", 0) > 120: # for each device, it checks if the devices has not been updated in 120 seconds. In that case, it delate all the deprecated devices
                    del data["devices"][id] 
            for id, service in list(data["services"].items()): # It works in the same way of the previuos for statement, but for services
                if now - service.get("time", 0) > 120:                    del data["services"][id]
            with open(self.json_file_name, "w") as f: # After any changes, overwrites the old catalog with the new one
                json.dump(data, f)

    def GET(self, *path, **query): # It handles HTTP requests to obtain catalog information
        with open(self.json_file_name, "r") as f:
            catalog = json.load(f)
        if len(path)==0:
            return json.dumps(catalog)
        if len(path) == 1 and path[0]=="broker":
            return json.dumps(catalog.get("broker"))        
        if len(path) == 1 and path[0] in ["devices", "services"]:
            return json.dumps(catalog.get(path[0]))
        if len(path) == 2 and path[0] in ["devices", "services"]:
            match = catalog[path[0]][path[1]]
            if match is None:
                raise cherrypy.HTTPError(404, f"{path[1]} not found")
            return json.dumps(match)
        raise cherrypy.HTTPError(400, "Invalid path")
    
    def POST(self, *path, **query): # It handles HTTP POST requests used to register a new device or service.
        body = json.loads(cherrypy.request.body.read()) # it reads the body (body structure at the bottom of the page)
        if path[0] not in ["services", "devices"] or len(path)>1:
            raise cherrypy.HTTPError(400, "Invalid path")
        with self.lock:
            with open(self.json_file_name, "r") as f: # it loads on data the content of catalog.json
                catalog = json.load(f)
            if path[1] in catalog[path[0]]: #TODO: check if correct, also in PUT
                raise cherrypy.HTTPError(409, f"{body['id']} already exists")
            else:
                body["time"]=time.time() #sets time to insertion time
                catalog[path[0]][body["id"]]=body
                with open(self.json_file_name, "w") as f:
                    json.dump(catalog, f) #saves to catalog
                return json.dumps(body) #returns the inserted body, with updated time stamp
            
            
    def PUT(self, *path, **query):  # It handles HTTP PUT requests used to update or refresh the time of an existing device/service registration.
        body = cherrypy.request.body.read()
        body = json.loads(body) if body else None
        if len(path)!=2 or path[0] not in ["services", "devices"]:
            raise cherrypy.HTTPError(400, "Invalid path")
        if body is None:
            raise cherrypy.HTTPError(404, f"{path[1]} not found")
        with self.lock:
            with open(self.json_file_name, "r") as f:
                catalog = json.load(f)
            if path[1] in catalog[path[0]]:
                
                body["time"]=time.time() #sets time to insertion time
                catalog[path[0]][body["id"]]=body 
                with open(self.json_file_name, "w") as f:
                    json.dump(catalog, f) #saves to catalog
                return json.dumps(body)
            body["time"] = time.time()
            catalog[path[0]][body["id"]]=body
            with open(self.json_file_name, "w") as f:
                json.dump(catalog, f)
            return json.dumps(body)

    # TODO: make body use path to delete
    def DELETE(self, *path, **query): # It handles HTTP DELETE requests used to remove a device or service from the Catalog
        if len(path) ==0 or len(path)>2 or path[0] not in ["services", "devices"]:
                raise cherrypy.HTTPError(400, "Invalid path")
        with self.lock: #modifies the catalog firstly loading it on data, then deleting the id-entry, and at last overwriting all on the catalog
            with open(self.json_file_name, "r") as f: 
                catalog = json.load(f)    
            if len(path) ==2:
                if path[1] not in catalog[path[0]]:
                    raise cherrypy.HTTPError(404, f"{path[1]} not found")
                del catalog[path[0]][path[1]]
            elif len(path)==1:
                catalog[path[0]] = []
            elif len(path)==1:
                catalog={}
                
            with open(self.json_file_name, "w") as f:
                    json.dump(catalog, f)
        return "Delete complete"

# body: 
# {
#   "id": "device_001",
#     "description": "Living room temperature sensor",
#     "endpoint": "http://localhost:8080/sensor/temperature",
#     "mqtt": {
#         "ip": "iot.eclipse.org",
#         "port": 1883,
#         "pub_topics": ["/tiot/group01/temperature"],
#         "sub_topics": []
#     },
#     "resources": ["temperature", "humidity"],
#     "time": time.time()
# }


# device = {
#     "id": "device_001",
#     "description": "Living room temperature sensor",
#     "endpoint": "http://localhost:8080/sensor/temperature",
#     "mqtt": {
#         "ip": "iot.eclipse.org",
#         "port": 1883,
#         "pub_topics": ["/tiot/group01/temperature"],
#         "sub_topics": []
#     },
#     "resources": ["temperature", "humidity"],
#     "time": time.time()
# }


# services = {
#   "id": "service_001",
#     "description": "Smart home device actuator",
#     "endpoint": "TODO",
#     "mqtt": {
#         "ip": "iot.eclipse.org",
#         "port": 1883,
#         "pub_topics": ["/tiot/group01/smartHome"],
#         "sub_topics": []
#     },
#     "resources": [TODO],
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




# with open(self.json_file_name, "r") as f: 
#                 catalog = json.load(f)
# {
#     "broker": {"ip": "iot.eclipse.org", "port": 1883},
#     "devices": [
#         {
#             "id": "sensor_01",
#             "description": "Living room temperature sensor",
#             "endpoint_url": "http://192.168.1.10:8080",
#             "mqtt": {"ip": "iot.eclipse.org", "port": 1883, "pub_topics": ["/tiot/group01/sensor_01/temp", "/tiot/group01/sensor_01/hum"], "sub_topics": ["/tiot/group01/sensor_01/commands/temp", "/tiot/group01/sensor_01/commands/hum"]},
#             "resources": ["temperature"],
#             "time": 1748000000.0
#         }
#     ],
#     "services": []
# }


# items = catalog.get(path[0], [])
# [
#     {
#         "id": "sensor_01",
#         "description": "Living room temperature sensor",
#         "endpoint_url": "http://192.168.1.10:8080",
#         "mqtt": {"ip": "iot.eclipse.org", "port": 1883, "pub_topics": ["/tiot/group01/sensors/temp"], "sub_topics": []},
#         "resources": ["temperature"],
#         "time": 1748000000.0
#     }
# ]