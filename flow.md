

* ESERCIZIO 11
    1. inizializzazione con richiesta di Broker e BrokerPort
    2. "start(self)" actions:
        * ci si connette ==> viene chiamata "on_connect(self)".
        * si chiama il loop di MQTT
        * si chiede al catalog gli arduino e gli actuators, si estrapolano i topics per il feedback e i command:
            * subscription al topic di feedback ARDUINO: ARDUINO_LED_FEEDBACK_TOPIC
            * subscription al topic di feedback ACTUATORS: ACTUATOR_FEEDBACK_TOPIC
        * prima di chiedere i comandi, si starta un thread parallelo per refreshare ogni 60 secs il service nel catalog. Si usa "loopRefresh(self, arduinoCommandTopic, actuatorCommandTopic)"
        * si chiama "self.commandLineLoop(self, commandTopicArduino, commandTopicActuator )" per chiedere i comandi man mano. 
        Ci sono le seguenti categorie di comando:
            * led 0 e led 1 per switchare il valore dei led dell'arduino
            * actuator temperature, actuator motion, actuator temperature ; con eventuali valori
        per ogni comando si controlla che sia stato scritto correttamente e si builda un JSON con "def buildCommand(self, target, value, room=None)" che builda delle risposte così: 
            {
                "command_id": str(uuid.uuid4()),
                "sender": "command_publisher_001",
                "target": target,
                "room": room,
                "action": "set",
                "value": value,
                "timestamp": time.time(),
                "reply_to": self.feedbackTopic
            }
    3. Quando l'user Quitta (scrivendo Q), si chiama la "stop(self, feedbackTopicArduino, feedbackTopicActuator)" in cui:
        * si fa unsubscribe dei due due topics di feedback
        * si stoppa il loop MQTT
        * ci si disconnette dal broker
  
  NB: Essendo il sistema di Actuators full REST, sarà MQTTActuatorBridge a gestire la fase intermedia tra il commandPublisher e l'ActuatorService


