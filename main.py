import cherrypy
from constants import PORT_NUMBER, HOST_NAME, CATALOG_URL, BROKER, PORT

# REST Services
from Catalog import Catalog

# MQTT Bridges
from MQTTCatalogBridge import MQTTCatalogBridge

if __name__ == "__main__":
    conf = {
        '/':{
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
        }
    }

    # Lab 10 needs the catalog both at root (/broker, /devices, ...)
    # and under /catalog for the newer Python clients.
    catalog = Catalog()
    cherrypy.tree.mount(catalog, '/', conf)
    cherrypy.tree.mount(catalog, '/catalog', conf)
    
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0', # Allows external connections
        'server.socket_port': PORT_NUMBER
    })
    
    # 2. Start CherryPy Engine (non-blocking)
    print("[Main] Starting CherryPy server...")
    cherrypy.engine.start()

    # 3. Start Background MQTT Catalog Bridge
    print("[Main] Starting MQTT Catalog Bridge...")
    
    catalog_bridge = MQTTCatalogBridge("catalog_bridge_group1", BROKER, PORT, CATALOG_URL)
    catalog_bridge.start()

    # 4. Block main thread to keep everything running
    cherrypy.engine.block()
