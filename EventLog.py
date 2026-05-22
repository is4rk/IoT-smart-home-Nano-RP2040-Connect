import cherrypy
import json
import time
from constants import *

queries = ["room", "since", "before", "type"]

class EventLog():
    exposed = True
   
    def __init__(self):
        self.logs = {}
        # debug string: if I reach the end of a request, served = True
        self.served = False

    def GET(self, *path, **query):
        # requesting all logs or filtering by query
        if (len(path) == 0):
            # case no queries, so all logs
            # GET /log
            if (len(query) == 0):
                # checking if logs is empty, using the fact that a collection is False if empty
                if self.logs:
                    self.served = True
                    # using json library to convert the logs into json
                    l = list(self.logs.values())
                    return json.dumps(l)
                # handling case logs are empty
                self.served = True
                return "Empty logs."
            # case queries, filtered logs
            # GET /log?<query>
            else:
                report = []
                for q in query:
                    if q not in queries:
                        raise cherrypy.HTTPError(404, "Bad query request.")
                    match(q):
                        case "room":
                            pass
                        case "since":
                            pass
                        case "before":
                            pass
                        case "type":
                            pass

                self.served = True
                return
        
        # checking all logs of a specific room
        # GET /log/<room>
        elif (len(path) == 1):
            name = "/log/" + path[0]
            if name in self.logs:
                self.served = True
                return json.dumps(self.logs[name])
            self.served = True
            return "Empty logs."

        # Error handling and served reset
        if self.served:
            self.served = False
            raise cherrypy.HTTPError(418, "Unresolved serve: I'm a teapot")
        self.served = False
        raise cherrypy.HTTPError(400, "Bad request: no services avaliable")

    def POST(self, *path):
        # appending one or more SenML events in the log
        # POST /log
        if(len(path) == 0):
            body = json.loads(cherrypy.request.body.read())
            # the body could contain one json entry, or a list of json entries
            for element in body:
                # cleaning the base name received
                bn = list(filter(lambda s : s != "", element["bn"].strip().split("/")))
                # new bn for log entry: /log/<room>
                log_bn = "/log/" + bn[len(bn)-1]

                # if there is already at least a measurement for that room, append the 
                # data received in the event array
                if log_bn in self.logs:
                    event = {}
                    event["n"] = element["e"][0]["n"]
                    event["u"] = element["e"][0]["u"]
                    event["v"] = element["e"][0]["v"]
                    event["t"] = time.time() - self.logs[log_bn]["bt"]
                    self.logs[log_bn]["e"].append(event)
                # else create a new room log
                else:
                    log = {}
                    log["bn"] = log_bn
                    log["bt"] = time.time()
                    log["e"] = []
                    log["e"] = element["e"]
                    log["e"][0]["t"] = 0
                    self.logs[log_bn] = log 
                

        
    def DELETE(self, *path, **query):
        if (len(path) == 0):
            # purging entries before a defined epoch
            # DELETE /log?before=<epoch>
            if(len(query) == 1):
                count = 0
                # checking if the query is "before"
                if "before" not in query:
                    raise cherrypy.HTTPError(400, "Bad request: no services avaliable")
                
                # find events to remove
                for room in self.logs.values():
                    bt = int(room["bt"])
                    # put them in a buffer
                    events_to_remove = []
                    for event in room["e"]:
                        if ((bt + int(event["t"])) < int(query["before"])):
                            events_to_remove.append(event)
                    # remove and count 
                    for event in events_to_remove:
                        count += 1
                        room["e"].remove(event)

                return ("Entries deleted: " + str(count))
            # purging all entries
            # DELETE /log
            else:
                count = 0
                # counting all events saved
                for room in self.logs.values():
                    count += len(room["e"])
                self.logs = {}
                return str(count)
        else:
            raise cherrypy.HTTPError(400, "Bad request: no services avaliable")
                

# Persistance through file save?
""" GET content to be done
        try:
            with open("log.json", mode="r", encoding="utf-8") as logFile:
                # if (len(path) == 0 or path[0] != "log"):
                    # raise cherrypy.HTTPError(400, "Invalid request or bad path")
                # if (len(path) == 2):

                # elif(len(query) == 1):

                # else:
                    print(json.load(logFile))
        except FileNotFoundError:
            print("Wrong file path")
"""