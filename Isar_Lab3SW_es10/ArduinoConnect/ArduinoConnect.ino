#include <WiFiNINA.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include "arduino_secrets.h"
#include <ArduinoHttpClient.h>
#include <MBED_RPi_Pico_TimerInterrupt.h>
#include <list>
#define DEBUG 0
#define USERNAME "arduino"
#define BASE_NAME "ArduinoGroup1"
#define HOST_NAME "127.0.0.1"
#define PORT_NUMB 8080

//So that i can avoid doing std::list
using namespace std;

//Wifi credentials 
char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

// Unique topic start
const String BASE_TOPIC = "/tiot/group1";
const String ID = "/arduino";
// Pins:
const int TEMP_PIN = A1;
const int GREEN_PIN = 2;
String REGISTRATION_DEVICES_TOPIC = BASE_TOPIC+"/catalog/devices/registration";
String REFRESH_DEVICE_TOPIC = BASE_TOPIC+"/catalog/devices/refresh";
// We had no access to a local LAN with internet connection, so we used an hotspot to
// test internet functionalities. However, internet providers don't allow connections on
// every port, so connecting to "test.mosquitto.org" on port 1883 was not possible.
// To test MQTT functionalities, we used the Mosquitto suite to set up a local broker
// on one of our computers.
// Not tested with public broker
// Broker address:
String broker_address = "test.mosquitto.org";;
int broker_port= 1883;


// Temperature conversion constants:
const int B = 4275;
const long int R0 = 100000;
const float VCC = 1023;
float temp = 0;

// Two global objects to store the sent and received JSON strings
// Capacity more then 1 SenML record
const int capacity = JSON_OBJECT_SIZE(2) + JSON_ARRAY_SIZE(1) + JSON_OBJECT_SIZE(4) + 100;
DynamicJsonDocument doc_snd(capacity);
DynamicJsonDocument doc_rec(capacity);


//clock for available subscription topics refresh
MBED_RPI_PICO_Timer ITimer1(1);
MBED_RPI_PICO_Timer ITimer2(2);

list<String> topics;
void refreshSub(uint allarm_num){
	TIMER_ISR_START(allarm_num);
	retriveTopic(topics);
	TIMER_ISR_END(allarm_num);
}

void refreshReg(uint allarm_num){
	TIMER_ISR_START(allarm_num);
	refresher();
	TIMER_ISR_END(allarm_num);
}



// WiFi declarations:
WiFiClient wifi;
int status = WL_IDLE_STATUS;
// The PubSubClient uses the WiFiClient to handle reception/transmission
// It also needs the broker address and port, the callback function reference 
PubSubClient client(broker_address.c_str(), broker_port, callback, wifi);

// Flexible SenML encoder funsction using ArduinoJson
template <typename T>
String senMlEncode(String res, T v, String uint) {
	// Initializa document
	doc_snd.clear();
	// Assign values
	doc_snd["bn"] = BASE_NAME;
	doc_snd["e"][0]["t"] = int(millis()/1000);
	doc_snd["e"][0]["n"] = res;
	doc_snd["e"][0]["v"] = v;
	doc_snd["e"][0]["u"] = uint;
	// Serialize output
	String output;
	serializeJson(doc_snd, output);
	return output;
}
void refresher(){
	String payload;
	registerDevice(); //TODO: removed payload from argument, investigate why it was given
	serializeJson(doc_snd, payload);
	client.publish(REFRESH_DEVICE_TOPIC.c_str(), payload.c_str()); // PUT to catalog
}
int GET(String& body, String path){
	HttpClient http = HttpClient(wifi, HOST_NAME, PORT_NUMB);
	http.beginRequest();
	http.get(path);
	http.endRequest();
	int response = http.responseStatusCode();
	body = http.responseBody();
	return response;
}

// Callback function called when a message arrives on a subscribed topic: 
void callback(char* topic, byte* payload, unsigned int length){
	if(DEBUG){
		Serial.print("Message arrived on topic: ");
		Serial.println(topic);
		Serial.print("Payload: ");
		for (int i = 0; i < length; i++) {
			Serial.print((char)payload[i]);
		}
		Serial.println();
	}

	// Try to deserialize the received Json
	DeserializationError err = deserializeJson(doc_rec, (char*) payload);
	// Error notification
	if (err){
		Serial.print(F("deserializeJson() failed with code "));
		Serial.println(err.c_str());
	}

	// Estract actuation information to use 
	const char* name = doc_rec["e"][0]["n"];
	int value = doc_rec["e"][0]["v"];

	if(DEBUG){
		Serial.print("Name: ");
		Serial.println(name);
		Serial.print("Value: ");
		Serial.println(value);
	}
	
	// Json actuation commands handler
	if (name != NULL && strcmp(name, "led") == 0) {
		if(value == 1){
			digitalWrite(GREEN_PIN, HIGH);
			if(DEBUG) Serial.println("LED ON");
		} else if (value == 0){
			digitalWrite(GREEN_PIN, LOW);
			if(DEBUG) Serial.println("LED OFF");
		}
	}
}
// Temperature sensor to Cel conversion function:
float tempConverter(int a){
	float R = ((VCC/(float) a) - 1)*R0;
	float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
	T = T - 273.15;
	return T;
}

void registerDevice() {
	doc_snd.clear();
	doc_snd["id"] = USERNAME;
	doc_snd["description"] = "Arduino temperature sensor and LED actuator";
	doc_snd["endpoint"] = "http://" + String(HOST_NAME) + ":" + String(PORT_NUMB);
	
	JsonObject mqtt = doc_snd.createNestedObject("mqtt");
	mqtt["ip"] = broker_address;
	mqtt["port"] = broker_port;
	
	JsonArray pub_topics = mqtt.createNestedArray("pub_topics");
	pub_topics.add(BASE_TOPIC + "/" + USERNAME + "/temperature");
	
	JsonArray sub_topics = mqtt.createNestedArray("sub_topics");
	sub_topics.add(BASE_TOPIC+"/"+USERNAME+"/commands/led");
	JsonArray resources = doc_snd.createNestedArray("resources");
	resources.add("temperature");
	resources.add("led");
	doc_snd["time"] = millis(); // Alternatively, you can sync via NTP if real epoch time is required
}

void reconnect() {
	while(client.state() != MQTT_CONNECTED) {
		if(DEBUG){
			Serial.print("Attempting MQTT connection to ");
			Serial.print(broker_address);
			Serial.print(":");
			Serial.println(broker_port);
		}

		// Try connecting to the broker with username [USERNAME] 
		if(client.connect(USERNAME)) {
			Serial.println("MQTT connected");
			// If connected, subscribe to topic [BASE_TOPIC]/led
			// To receive actuation commands
			for(const String& topic : topics){
				client.subscribe(topic.c_str());
			}
			String payload;
			registerDevice();
			serializeJson(doc_snd, payload);
			client.publish(REGISTRATION_DEVICES_TOPIC.c_str(), payload.c_str()); // TODO: make it do a PUT to refresh the device, need to be added in the MQTT bridge

		} else { 
			// If connection fails, retry after 5 sec
			Serial.print("failed, rc=");
			Serial.print(client.state());
			Serial.println(" try again in 5 seconds");
			delay(5000);
		}
	}
}

void retriveTopic(list<String>& topics){
	topics.clear();
	String devTopicsStr;
	GET(devTopicsStr, "/catalog/devices");
	DeserializationError err = deserializeJson(doc_rec, devTopicsStr);
	if (err){
		Serial.print(F("deserializeJson() failed with code "));
		Serial.println(err.c_str());
	}
	
	for(JsonPair keyVal : doc_rec.as<JsonObject>()){	 
		JsonArray topicsJ = keyVal.value()["mqtt"]["sub_topics"];
		for(JsonVariant topicJ : topicsJ){
			String topicStr= topicJ.as<String>();
			topics.push_back(topicStr);
		}
	}

	String serTopicsStr;
	GET(serTopicsStr, "/catalog/services");
	err = deserializeJson(doc_rec, serTopicsStr);
	// Error notification
	if (err){
		Serial.print(F("deserializeJson() failed with code "));
		Serial.println(err.c_str());
	}

	for(JsonPair keyVal : doc_rec.as<JsonObject>()){	 
		JsonArray topicsJ= keyVal.value()["mqtt"]["sub_topics"];
		for(JsonVariant topicJ : topicsJ){
			String topicStr= topicJ.as<String>();
			topics.push_back(topicStr);
		}
	}
}

void setup() {
	// Serial start:
	Serial.begin(9600);
	while(!Serial);
	Serial.println("Serial connected");
	// Pin modes:
	pinMode(TEMP_PIN, INPUT);
	pinMode(GREEN_PIN, OUTPUT);
	// WiFi connection start:
	while (status != WL_CONNECTED){
		Serial.println("Attempting to connect to SSID: ");
		Serial.println(ssid);
		status = WiFi.begin(ssid, pass);
		delay(10000);
	}
	// Connection successful info:
	Serial.print("Connected with IP address: ");
	Serial.println(WiFi.localIP());
	
	//Gets broker info
	String body;
	GET(body, "/catalog/broker");
	DeserializationError err = deserializeJson(doc_rec, body);
	if (err){
		Serial.print(F("deserializeJson() failed with code "));
		Serial.println(err.c_str());
	}
	broker_address = doc_rec["ip"].as<String>();
	broker_port = doc_rec["port"].as<int>();
	
	//Starts topics sub timer
	ITimer1.setInterval(120000, refreshSub);
	retriveTopic(topics);

	//Starts refresh timer
	ITimer1.setInterval(60000, refreshReg);
}

// Main loop:
void loop() {
	// Last message time to have a non blocking delay
	static unsigned long lastMsg = 0;
	// Check the connection to the broker
	if(client.state() != MQTT_CONNECTED) {
		// Reconnect if needed
		if(DEBUG) Serial.println("Client disconnected, reconnecting...");
		reconnect();
	}

	// Check incoming messages on subscribed topics
	client.loop();

	// Wait 10sec without blocking the code to receive messages
	if(millis() - lastMsg > 10000){
		lastMsg = millis();
		float temp = tempConverter(analogRead(TEMP_PIN));

		// Create the payload and the topic (dedicated variable for debugging)
		String payload = senMlEncode("temperature", temp, "Cel");
		String topic = BASE_TOPIC + "/"+USERNAME +String("/temperature");

		if(DEBUG) {
			Serial.println("Payload: ");
			Serial.println(payload);
			Serial.print("On topic: ");
			Serial.println(topic);
		}
		
		// Publish the temperature on the topic
		client.publish(topic.c_str(), payload.c_str());
	}
	
	// Wait to not overload
	delay(100);
}