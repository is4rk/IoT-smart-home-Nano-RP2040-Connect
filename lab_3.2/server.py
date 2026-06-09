import cherrypy
import json

# Make it visible to the network
HOST_NAME = "0.0.0.0"
PORT_NUMB = 9966

class TempLog():
    exposed = True
   
    # Initialize a empty list in the class
    def __init__(self):
        self.logs = []

    # GET request handling
    def GET(self, *path, **query):
        # requesting all logs 
        if (len(path) == 0):
            # GET /log
            # ignoring queries
            if (self.logs):
                return json.dumps(self.logs)
            return "Empty logs."
        # else bad request
        else:
            raise cherrypy.HTTPError(404, "Bad request.")
    
    # POST request handling
    def POST(self, *path, **query):
        # adding a temperature event on the list
        if(len(path) == 0):
            # POST /log
            # ignoring queries
            body = json.loads(cherrypy.request.body.read())
            self.logs.append(body)
            return "Logs updated"
        # else bad request
        else:
            raise cherrypy.HTTPError(404, "Bad request.")

if __name__ == "__main__":
    conf = {
        '/':{
            'request.dispatch':cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on':True,
        }
    }

    # service mounting section
    cherrypy.tree.mount(TempLog(), '/log', conf)
    
    # host config
    # default is http://127.0.0.1:8080
    cherrypy.config.update({'server.socket_host': HOST_NAME})
    cherrypy.config.update({'server.socket_port': PORT_NUMB})
    
    # start
    cherrypy.engine.start()
    cherrypy.engine.block()