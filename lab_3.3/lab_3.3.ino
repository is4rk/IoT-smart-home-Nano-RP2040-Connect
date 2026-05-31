#include <WiFiNINA.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include "arduino_secrets.h"

#define DEBUG 0
#define USERNAME "TiotGroup1"
#define BASE_NAME "ArduinoGroup1"

// Unique topic start
const String BASE_TOPIC = "/tiot/group1";

// Pins:
const int TEMP_PIN = A1;
const int GREEN_PIN = 2;

// We had no access to a local LAN with internet connection, so we used an hotspot to
// test internet functionalities. However, internet providers don't allow connections on
// every port, so connecting to "test.mosquitto.org" on port 1883 was not possible.
// To test MQTT functionalities, we used the Mosquitto suite to set up a local broker
// on one of our computers.
// Not tested with public broker
// Broker address:
String broker_address = "test.mosquitto.org";
int broker_port = 1883;

// WiFi credentials:
char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

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

// WiFi declarations:
WiFiClient wifi;
int status = WL_IDLE_STATUS;
// The PubSubClient uses the WiFiClient to handle reception/transmission
// It also needs the broker address and port, the callback function reference 
PubSubClient client(broker_address.c_str(), broker_port, callback, wifi);

// Flexible SenML encoder funsction using ArduinoJson
template <typename T>
String senMlEncode(String res, T v, String unit) {
  // Initializa document
  doc_snd.clear();
  // Assign values
  doc_snd["bn"] = BASE_NAME;
  doc_snd["e"][0]["t"] = int(millis()/1000);
  doc_snd["e"][0]["n"] = res;
  doc_snd["e"][0]["v"] = v;
  doc_snd["e"][0]["u"] = unit;
  // Serialize output
  String output;
  serializeJson(doc_snd, output);
  return output;
}

// Temperature sensor to Cel conversion function:
float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
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
      client.subscribe((BASE_TOPIC + String("/led")).c_str());
    } else {
      // If connection fails, retry after 5 sec
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
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
    String topic = BASE_TOPIC + String("/temperature");

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

