import cherrypy
import json
import time
import threading
class Catalog:
    def __init__(self):
        threading.Thread(target=self._cleanup_loop, daemon=True).start()
        cat_dict=json.loads()  
    def _cleanup_loop(self):
        pass
    def GET(self, *path, **query):
        pass
    def POST(self, *path, **query):
        pass
    def PUT(self, *path, **query):
        pass
    def DELETE(self, *path, **query):
        pass
    