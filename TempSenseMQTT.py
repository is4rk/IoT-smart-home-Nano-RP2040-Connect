from DeviceMQTTClient import DeviceMQTTClient as mqttCli

class TempSenseMQTT:
    def __init__(self):
        self.mqttCli = mqttCli()
        self.broker= self.mqttCli.getBroker()
        self.port=self.mqttCli.getPort()