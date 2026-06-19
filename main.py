import cherrypy
from constants import PORT_NUMBER, HOST_NAME, CATALOG_URL, BROKER, PORT

# REST Services
from EventLog import EventLog
from Catalog import Catalog
from SmartHomeSensorService import SmartHomeSensorService

# MQTT Bridges
from MQTTCatalogBridge import MQTTCatalogBridge
from MQTTActuatorBridge import MQTTActuatorBridge

if __name__ == "__main__":
    conf = {
        '/':{
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.sessions.on': True,
        }
    }

    # 1. Mount CherryPy REST Services
    cherrypy.tree.mount(EventLog(), '/log', conf)
    cherrypy.tree.mount(Catalog(), '/catalog', conf)
    cherrypy.tree.mount(SmartHomeSensorService(), '/sensor', conf)
    
    cherrypy.config.update({
        'server.socket_host': '0.0.0.0', # Allows external connections
        'server.socket_port': PORT_NUMBER
    })
    
    # 2. Start CherryPy Engine (non-blocking)
    print("[Main] Starting CherryPy server...")
    cherrypy.engine.start()

    # 3. Start Background MQTT Bridges
    print("[Main] Starting MQTT Bridges...")
    
    catalog_bridge = MQTTCatalogBridge("catalog_bridge_group1", BROKER, PORT, f"{CATALOG_URL}/catalog")
    catalog_bridge.start()
    
    actuator_bridge = MQTTActuatorBridge("actuator_bridge_group1", rest_base_url=f"{CATALOG_URL}/sensor")
    actuator_bridge.start()

    # 4. Block main thread to keep everything running
    cherrypy.engine.block()