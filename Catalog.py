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
                if now - device["element"]["time"] > 120: # for each device, it checks if the devices has not been updated in 120 seconds. In that case, it delate all the deprecated devices
                    del data["devices"][id] 
            for id, service in list(data["services"].items()): # It works in the same way of the previuos for statement, but for services
                if now - service["element"]["time"] > 120:
                    del data["services"][id]
            with open(self.json_file_name, "w") as f: # After any changes, overwrites the old catalog with the new one
                json.dump(data, f)

    def GET(self, *path, **query): # It handles HTTP requests to obtain catalog information
        with self.lock:
            with open(self.json_file_name, "r") as f:
                return json.load(f)

    def POST(self, *path, **query): # It handles HTTP POST requests used to register a new device or service.
        body = json.loads(cherrypy.request.body.read()) # it reads the body (body structure at the bottom of the page)
        elementType = "devices" if body["type"]=="device" else "services" # It check if it is a device or a service
        body["element"]["time"]=time.time() # update the time
        with self.lock:
            with open(self.json_file_name, "r") as f: # it loads on data the content of catalog.json
                data = json.load(f)
            data[elementType][body["element"]["id"]]=body # then update the id of the device or service
            with open(self.json_file_name, "w") as f:
                json.dump(data, f) # upload the modified catalog

    def PUT(self, *path, **query):  # It handles HTTP PUT requests used to update or refresh the time of an existing device/service registration.
        body = json.loads(cherrypy.request.body.read()) #it loads on body the body of the PUT request
        elementType = "devices" if body["type"]=="device" else "services" #as in the POST, it check if it is a device or a service
        body["element"]["time"]=time.time() #updating the time of device or service
        id_to_update = body["element"]["id"] #it extract the serivce/device's id to update
        with self.lock: # like the previous function, the following lines extract the catalog on a data, update the body antìd then load on the catalog the modifies
            with open(self.json_file_name, "r") as f:
                data = json.load(f)
            data[elementType][id_to_update]=body
        
            with open(self.json_file_name, "w") as f:
                json.dump(data, f)

    def DELETE(self, *path, **query): # It handles HTTP DELETE requests used to remove a device or service from the Catalog
        body = json.loads(cherrypy.request.body.read()) # extract the body
        elementType = "devices" if body["type"]=="device" else "services" #check the type
        id_to_delete = body["element"]["id"] # extract the id to delete
        with self.lock: #modifies the catalog firstly loading it on data, then deleting the id-entry, and at last overwriting all on the catalog
            with open(self.json_file_name, "r") as f: 
                data = json.load(f)
            del data[elementType][id_to_delete] 
            with open(self.json_file_name, "w") as f:
                json.dump(data, f)

# body = {
#   "type": "device/service",
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