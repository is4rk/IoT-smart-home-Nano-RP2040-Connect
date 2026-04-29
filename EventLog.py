import cherrypy
import json
import time
from constants import *

queries = ["room", "since", "before", "type"]

class EventLog():
    exposed = True
   
    def __init__(self):
        self.logs = []
        # debug string: if I reach the end of a request, served = True
        self.served = False

    def GET(self, *p, **q):
        # requesting all logs or filtering by query
        if (len(p) == 0):
            # case no queries, so all logs
            # GET /log
            if (len(q) == 0):
                # checking if logs is empty, using the fact that a collection is False if empty
                if self.logs:
                    self.served = True
                    # using json library to convert the logs into json
                    return json.dumps(self.logs)
                # handling case logs are empty
                self.served = True
                return "Empty logs."
            # case queries, filtered logs
            # GET /log?<query>
            else:
                report = []
                # TODO: query lookinto
                self.served = True
                return
        
        # checking all logs of a specific room
        # GET /log/<room>
        elif (len(p) == 1):
            report = []
            # checking if it's a valid room
            if p[0] in rooms: 
                # checking if the logs are not empty
                if self.logs:
                    self.served = True
                    # for each sensor log entry, take the bn and make it as a list of strings,
                    # then check if the log room is equal to the filter room
                    # if true, append the log entry to the report list, 
                    # which will be returned in the payload as a json
                    for log in self.logs:
                        bn = list(filter(lambda s : s != "", log["bn"].strip().split("/")))
                        if bn[len(bn) - 2] == p[0]:
                            report.append(log)
                if report:
                    self.served = True
                    return json.dumps(report)
                # handling case no logs or no logs matching the room so empty report
                self.served = True
                return "Empty logs."



        # Error handling and served reset
        if self.served:
            self.served = False
            raise cherrypy.HTTPError(418, "Unresolved serve: I'm a teapot")
        self.served = False
        raise cherrypy.HTTPError(400, "Bad request: no services avaliable")

    def POST(self, *p):
        # appending one or more SenML events in the log
        # POST /log
        if(len(p) == 0):
            body = json.loads(cherrypy.request.body.read())
            for element in body:
                # entries with bn, bt, n, u, v
                """
                {
                    "bn": "http://127.0.0.1:9090/sensor/living_room",
                    "bt": 1777420801.125,
                    "e": [
                        {
                            "n": "humidity",
                            "u": "%RH",
                            "v": 45.2
                        }
                    ]
                }
                """
                bn = list(filter(lambda s : s != "", element["bn"].strip().split("/")))
                print(str(bn)) 

                """
                {
                    "bn": "http://127.0.0.1:9090/sensor/living_room",
                    "bt": 1777420801.125,
                    "e": [
                        {
                            "n": "humidity",
                            "u": "%RH",
                            "v": 45.2
                        }
                    ]
                }
                """


        
    def DELETE(self, *p, **q):
        if (len(p) == 0):
            # purging entries before a defined epoch
            # DELETE /log?before=<epoch>
            if(len(q) == 1):
                return
            # purging all entries
            # DELETE /log
            else:
                # TODO: counting entries
                self.logs = []
                return str(0)
                

# Persistance through file save?
""" GET content to be done
        try:
            with open("log.json", mode="r", encoding="utf-8") as logFile:
                # if (len(p) == 0 or p[0] != "log"):
                    # raise cherrypy.HTTPError(400, "Invalid request or bad path")
                # if (len(p) == 2):

                # elif(len(q) == 1):

                # else:
                    print(json.load(logFile))
        except FileNotFoundError:
            print("Wrong file path")
"""