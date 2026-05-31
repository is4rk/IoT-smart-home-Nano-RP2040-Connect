import cherrypy
import requests
import json
import time
from threading import Lock
import paho.mqtt.client as PahoMQTT
from SmartHomeSensorService import controlSenML
from constants import *

queries = ["room", "since", "before", "type"]
CATALOG_URL = "http://localhost:8080/catalog"

class EventLog():
    exposed = True
   
    def __init__(self, clientID="event_log"):
        self.clientID = clientID
        self.logs = []
        self.lock = Lock()
        self.catalog_url = CATALOG_URL
        self.broker = None
        self.port = None
        self.mqtt_started = False
        self.next_id = 1
        self.get_mqtt_broker()

        self.client = PahoMQTT.Client(self.clientID)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.last_response=None
        self.start()

    # MQTT

    def get_mqtt_broker(self):
        response = requests.get(f"{self.catalog_url}/broker")
        metadata = response.json()
        self.broker = metadata["ip"]
        self.port = metadata["port"]

    def start(self):
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        # Placeholder: subscribe to relevant topics here, e.g. sensor readings and actuator commands
        # Example: self.client.subscribe("/tiot/group1/temperature/+")
        return

    def on_message(self, client, userdata, msg):
        # Ingest SenML payloads from MQTT; normalize similar to POST handling
        raw = msg.payload
        if isinstance(raw, (bytes, bytearray)):
            try:
                raw = raw.decode("utf-8")
            except Exception:
                return

        try:
            # unwrap repeatedly in case of double-encoded JSON
            while isinstance(raw, str):
                raw = json.loads(raw)
        except Exception:
            return

        records = []
        if isinstance(raw, dict):
            records = [raw]
        elif isinstance(raw, list):
            records = raw
        else:
            return

        added = 0
        for rec in records:
            try:
                if not controlSenML(rec):
                    continue
            except Exception:
                continue

            rec["bt"] = time.time()
            with self.lock:
                rec["log_id"] = str(self.next_id)
                self.next_id += 1
                self.logs.append(rec)
                added += 1

        if added:
            self.last_response = f"Added {added} records from MQTT"


    # REST 

    def GET(self, *path, **query):
        # requesting all logs or filtering by query
        if (len(path) == 0):
            # GET /log
            if (len(query) == 0):
                with self.lock:
                    snapshot = list(self.logs)
                return json.dumps(snapshot)

            # GET /log?<query>
            for q in query:
                if q not in queries:
                    raise cherrypy.HTTPError(404, "Bad query request.")

            report = []
            with self.lock:
                snapshot = list(self.logs)

            for event in snapshot:
                keep = True
                for q in query:
                    match(q):
                        case "room":
                            if not (event["bn"].startswith("/sensor/" + query["room"]) or event["bn"].startswith("/" + query["room"])):
                                keep = False
                        case "since":
                            if float(event["bt"]) < float(query["since"]):
                                keep = False
                        case "before":
                            if float(event["bt"]) >= float(query["before"]):
                                keep = False
                        case "type":
                            if event["e"][0]["n"] != query["type"]:
                                keep = False

                if keep:
                    report.append(event)

            return json.dumps(report)
        
        # checking all logs of a specific room
        # GET /log/<room>
        elif (len(path) == 1):
            report = []
            with self.lock:
                snapshot = list(self.logs)

            for event in snapshot:
                if event["bn"].startswith("/sensor/" + path[0]) or event["bn"].startswith("/" + path[0]):
                    report.append(event)

            return json.dumps(report)

        # Error handling 
        raise cherrypy.HTTPError(400, "Bad request: no services avaliable")

    def POST(self, *path):
        # appending one or more SenML events in the log
        # POST /log
        if(len(path) == 0):
            raw = cherrypy.request.body.read()
            if isinstance(raw, (bytes, bytearray)):
                try:
                    raw = raw.decode("utf-8")
                except Exception:
                    raise cherrypy.HTTPError(422, "Wrong data fromat.")

            try:
                while isinstance(raw, str):
                    raw = json.loads(raw)
            except Exception:
                raise cherrypy.HTTPError(422, "Wrong data fromat.")

            records = []
            if isinstance(raw, dict):
                records = [raw]
            elif isinstance(raw, list):
                records = raw
            else:
                raise cherrypy.HTTPError(422, "Wrong data fromat.")

            added = 0
            for rec in records:
                if not isinstance(rec, dict) or not controlSenML(rec):
                    raise cherrypy.HTTPError(422, "Wrong data fromat.")
                rec["bt"] = time.time()
                with self.lock:
                    rec["log_id"] = str(self.next_id)
                    self.next_id += 1
                    self.logs.append(rec)
                    added += 1

            return ("Events registered: " + str(added))
        else:
            raise cherrypy.HTTPError(400, "Bad request: no services avaliable")
        
    def DELETE(self, *path, **query):
        if (len(path) == 0):
            # purging entries before a defined epoch
            # DELETE /log?before=<epoch>
            if(len(query) == 1):
                count = 0
                # checking if the query is "before"
                if "before" not in query:
                    raise cherrypy.HTTPError(400, "Bad request: no services avaliable")
                
                events_to_remove = []
                with self.lock:
                    # find events to remove
                    for event in self.logs:
                        # put them in a buffer
                        if (float(event["bt"]) < float(query["before"])):
                            events_to_remove.append(event)
                    # remove and count
                    for e in events_to_remove:
                        count += 1
                        self.logs.remove(e)
                return ("Entries deleted: " + str(count))
            # purging all entries
            # DELETE /log
            elif (len(query) == 0):
                with self.lock:
                    count = len(self.logs)
                    self.logs = []
                return str(count)
            else:
                raise cherrypy.HTTPError(400, "Bad request: no services avaliable")
        else:
            raise cherrypy.HTTPError(400, "Bad request: no services avaliable")
    
    # MQTT