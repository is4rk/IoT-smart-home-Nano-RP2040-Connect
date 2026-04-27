import cherrypy
from EventLogger import EventLogger 

if __name__ == "__main__":
    conf = {
        '/':{
            'request.dispatch':cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on':True,
        }
    }

    # service mounting section
    cherrypy.tree.mount(EventLogger(), '/string', conf)
    
    # host config
    # default is http://127.0.0.1:8080/

    # cherrypy.config.update({'server.socket_host':'0.0.0.0'})
    # cherrypy.config.update({'server.socket_port': 9090})
    
    # start
    cherrypy.engine.start()
    cherrypy.engine.block()
