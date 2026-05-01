import cherrypy
import json
import time
import random
from constants import *

def controlSenML(d):
    
    if not(len(d.keys()) == 3):
        return False
    for k in d.keys():
        if k not in SENMLdatas: return False
        
    eventDict = d["e"][0]
    if not(len(eventDict.keys()) == 3):
        return False
    for k in eventDict.keys():
        if k not in eDatas: return False
    return True


class SmartHomeSensorService():

    exposed = True

    actuatorsStates ={
        "thermostat": 0,
        "lights": False,
        "blinds": 0
    }


    def GET(self, *path, **query):

        # /sensor/<room>/<type>
        if(len(path) != 2):
             raise cherrypy.HTTPError(404, "len path invalid") 
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
                        (f"{"v" if value not in [True, False ] else "bv"}"): value
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
                    unit = "%RH"
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
                        (f"{"v" if value not in [True, False ] else "bv"}"): value
                    }
                ]
            }   
            return json.dumps(result)
        else:
            raise cherrypy.HTTPError(404, "invalid path") 
            
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
                        unit = "%\position"
                        self.actuatorsStates["blinds"] = data["e"][0]["v"]
                    case "lights":
                        unit = "boolean"
                        self.actuatorsStates["lights"] = data["e"][0]["bv"]                   
        else:
            raise cherrypy.HTTPError(404, "invalid path") 
    

