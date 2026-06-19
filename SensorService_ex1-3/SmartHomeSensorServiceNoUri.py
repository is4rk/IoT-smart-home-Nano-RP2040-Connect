# Exercise 1: First version of Sensor service, without uri

import cherrypy
import json
import time
import random
from constants import *

class SmartHomeSensorServiceNoUri():
    exposed = True
    
    def GET(self, **query):
        cherrypy.response.headers['Content-Type'] = 'application/json'
        
        room = query.get('room')
        sensor_type = query.get('sensor_type')
        
        # Check if sensor and room are ok
        if room is None or room not in rooms:
            raise cherrypy.HTTPError(404, json.dumps({
                "error": "room not found",
                "available_rooms": rooms
            }))
        
        if sensor_type is None or sensor_type not in sensors:
            raise cherrypy.HTTPError(400, json.dumps({
                "error": "unknown sensor type",
                "valid_types": sensors
            }))
        
        bn = "/sensor/" + room
        bt = time.time()
        
        # Random values
        if sensor_type == "temperature":
            unit = units[0]  
            value = random.uniform(5, 30)
            use_bv = False
        elif sensor_type == "humidity":
            unit = "%RH"
            value = random.uniform(20, 80)
            use_bv = False
        elif sensor_type == "motion":
            unit = "boolean"
            value = random.choice([True, False])
            use_bv = True
        
        result = {
            "bn": bn,
            "bt": bt,
            "e": [
                {
                    "n": sensor_type,
                    "u": unit,
                    ("bv" if use_bv else "v"): value
                }
            ]
        }
        return json.dumps(result)

if __name__ == '__main__':
    cherrypy.tree.mount(SmartHomeSensorServiceNoUri())
    cherrypy.engine.start()
    cherrypy.engine.block()
