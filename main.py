import cherrypy
from constants import PORT_NUMBER, HOST_NAME
from EventLog import EventLog
from Catalog import Catalog
from SmartHomeSensorService import SmartHomeSensorService

if __name__ == "__main__":
    conf = {
        '/':{
            'request.dispatch':cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on':True,
        }
    }

    # service mounting section
    # EventLog is disabled for now (not started)
    cherrypy.tree.mount(EventLog(), '/log', conf)
    cherrypy.tree.mount(Catalog(), '/catalog', conf)
    cherrypy.tree.mount(SmartHomeSensorService(), '/sensor', conf)
    # no EventLog startup subscription
    
    # host config
    # default is http://127.0.0.1:8080

    cherrypy.config.update({'server.socket_host': HOST_NAME})
    cherrypy.config.update({'server.socket_port': PORT_NUMBER})
    
    # start
    cherrypy.engine.start()
    cherrypy.engine.block()
