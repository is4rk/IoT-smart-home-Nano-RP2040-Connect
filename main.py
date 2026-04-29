import cherrypy
from constants import PORT_NUMBER, HOST_NAME
from EventLog import EventLog

if __name__ == "__main__":
    conf = {
        '/':{
            'request.dispatch':cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on':True,
        }
    }

    # service mounting section
    cherrypy.tree.mount(EventLog(), '/log', conf)
    
    # host config
    # default is http://127.0.0.1:8080/

    cherrypy.config.update({'server.socket_host': HOST_NAME})
    cherrypy.config.update({'server.socket_port': PORT_NUMBER})
    
    # start
    cherrypy.engine.start()
    cherrypy.engine.block()
