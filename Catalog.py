import cherrypy
import json
import time
import threading
class Catalog:
    def __init__(self):
        threading.Thread(target=self._cleanup_loop, daemon=True).start()
        cat_dict=json.loads()
        self.json_file_name="catalog.json"

    def _cleanup_loop(self):
        pass
    def GET(self, *path, **query):
        with open(self.json_file_name, "r") as f:
            return json.loads(f)
    def POST(self, *path, **query):
        body = json.loads(cherrypy.request.body.read())
        with open(self.json_file_name, "w") as f:
            json.dumps(f, body) #qualcosa
    def PUT(self, *path, **query):
        pass
    def DELETE(self, *path, **query): #to finish at home
        body = json.load(cherrypy.request.body.read())
        
        with open(self.json_file_name, "r") as f:
            data = json.load(f)
        id_to_delete=body["ID"]
        del data[id_to_delete] #TO CONTROL
        with open(self.json_file_name, "w") as f:
            pass