# Exercise 2, 3 and 6: Smart Home Sensor and Actuator Service, with catalog implementation, 
import cherrypy
import json
import time
import random
import threading
from CatalogClient import CatalogClient
from constants import *


def controlSenML(d):
    # Check main structure safely
    if "e" not in d or "bn" not in d:
        return False
        
    eventDict = d["e"][0]
    
    # Require name and unit
    if "n" not in eventDict or "u" not in eventDict:
        return False
        
    # Require at least a value type
    if "v" not in eventDict and "bv" not in eventDict:
        return False
        
    return True


class SmartHomeSensorService():
    # Init and try to register to the catalog
    def __init__(self):
        self.catalog_client=CatalogClient(CATALOG_URL)
        self.service_payload = {
            "id": "Service001",
            "description": "Smart Home Sensor Service",
            "endpoint_url": "http://localhost:8081",
            "resources": ["temperature", "humidity", "motion"]
        }

        try:
            self.catalog_client.register_service(self.service_payload)
        except Exception as e:
            print(f"WARNING: could not register on startup: {e}")

        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()
    
    def _refresh_loop(self):
        while True:
            time.sleep(60)
            try:
                id = random.randint(1, 100)
                actuatorServiceID = f"actuator_service_{id}"
                self.catalog_client.refresh_service(
                    self.service_payload["id"],
                    self.service_payload
                )
            except Exception as e:
                print(f"WARNING: could not refresh registration, retrying next cycle: {e}")

    exposed = True

    actuatorsStates ={
        "thermostat": 0,
        "lights": False,
        "blinds": 0
    }


    # GET: retrieve informations, changing depending on the uri
    # It is a simulation and we use random uniform to generate values for sensors
    def GET(self, *path, **query):
        # /sensor/<room>/<type>
        if(len(path) != 2):
            raise cherrypy.HTTPError(404, "len path invalid") 
        # Handling if it is a sensor or an actuator
        if(len(path) == 2 and path[0] in rooms and path[1] in sensors):
            bn = "/sensor/" + path[0] 
            bt = time.time()
            name = path[1]
            match path[1]:
                case "temperature":
                    unit = f"{units[0]}"
                    value = random.uniform(5, 30)
                case "humidity":
                    unit = "%RH"
                    value = random.uniform(20, 80)
                case "motion":
                    unit = "boolean"
                    value = random.choice([True , False])
            
            result = {
                "bn": bn,
                "bt": bt,
                "e" :[
                    {
                        "n":name,
                        "u": unit,
                        ("v" if value not in [True, False] else "bv"): value
                    }
                ]
            }
            
            return json.dumps(result)
        
        # type in actuators
        if(len(path) == 2 and path[0] in rooms and path[1] in actuators):
            bn = "/sensor/" + path[0] 
            bt = time.time()
            name = path[1]
            match path[1]:
                case "thermostat":
                    unit = f"{units[0]}"
                    value = self.actuatorsStates["thermostat"]
                case "blinds":
                    unit = "% position"
                    value = self.actuatorsStates["blinds"]
                case "lights":
                    unit = "boolean"
                    value = self.actuatorsStates["lights"]      

            result = {
                "bn": bn,
                "bt": bt,
                "e" :[
                    {
                        "n":name,
                        "u": unit,
                        ("v" if value not in [True, False] else "bv"): value
                    }
                ]
            }   
            return json.dumps(result)
        else:
            raise cherrypy.HTTPError(404, "invalid path") 
    
    # POST: update the state of actuators with the infors arriving in the body
    def POST(self, *path, **query):
        # type in actuators
        if(len(path) == 2 and path[0] in rooms and path[1] in actuators):
            body = cherrypy.request.body.read()
            data = json.loads(body)

            flag422 = controlSenML(data)
            if(flag422 == False): 
                raise cherrypy.HTTPError(422, "Invalid senML format") 

            name = data["e"][0]["n"]
            if(name != path[1]): raise cherrypy.HTTPError(400, "path not match senml data")  
                
            match path[1]:
                case "thermostat":
                    unit = "Celsius"
                    self.actuatorsStates["thermostat"] = data["e"][0]["v"]
                case "blinds":
                    unit = "% position"
                    self.actuatorsStates["blinds"] = data["e"][0]["v"]
                case "lights":
                    unit = "boolean"
                    self.actuatorsStates["lights"] = data["e"][0]["bv"]                   
        else:
            raise cherrypy.HTTPError(404, "invalid path") 
 #for testing
if __name__ == '__main__':
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        }
    }
    
    cherrypy.tree.mount(SmartHomeSensorService(), '/sensor', conf)
    cherrypy.config.update({
            'server.socket_host': '0.0.0.0', 
            'server.socket_port': 8081
        })    
    cherrypy.engine.start()
    cherrypy.engine.block()