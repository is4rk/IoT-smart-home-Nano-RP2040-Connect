import cherrypy
import json
import time
import random
from constants import *

class SmartHomeSensorService():

    exposed = True



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
        else:
            raise cherrypy.HTTPError(404, "invalid path") 
            

    

