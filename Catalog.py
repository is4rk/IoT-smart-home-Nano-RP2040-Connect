import cherrypy
import json
import time
import threading
class Catalog:
    def __init__(self):
        threading.Thread(target=self._cleanup_loop, daemon=True).start()
    def _cleanup_loop(self):
        pass
    