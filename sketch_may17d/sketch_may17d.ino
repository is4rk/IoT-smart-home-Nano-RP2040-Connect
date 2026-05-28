#include <WiFiNINA.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include "arduino_secrets.h"

String broker_address="test.mosquitto.org";
int broker_port = 1883;
const String base_topic = "/tiot/0";
const int TEMP_PIN = A1;
const int LED_PIN = 4;
const int B = 4275;
const long int R0 = 100000;
const float VCC =1023;
float temp=0;
const int capacity = JSON_OBJECT_SIZE(2) + JSON_ARRAY_SIZE(1) + JSON_OBJECT_SIZE(4) + 100;
DynamicJsonDocument doc_snd(capacity);
DynamicJsonDocument doc_rec(capacity);
WiFiClient wifi;

int status = WL_IDLE_STATUS;

void callback(char* topic, byte* payload, unsigned int length){
  DeserializationError err = deserializeJson(doc_rec, (char*) payload);
  if (err){
    Serial.print(F("deserialzieJson() failed with code "));
    Serial.println(err.c_str());
  }
  if (doc_rec["e"][0]["n"]=="led"){
    if(doc_rec["e"][0]["v"]==1){
      digitalWrite(LED_PIN, HIGH);
    } else if (doc_rec["e"][0]["v"]==0){
      digitalWrite(LED_PIN,LOW);
    }
  }
}

PubSubClient client(broker_address.c_str(), broker_port, callback, wifi);

float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
}

String senMlEncode(String res, float v, String unit){
  doc_snd.clear();
  doc_snd["bn"]="ArduinoGroup1";
  doc_snd["e"][0]["t"] = int(millis()/1000);
  doc_snd["e"][0]["n"] = res;
  doc_snd["e"][0]["v"] = v;
  doc_snd["e"][0]["u"] = unit;
  String output;
  serializeJson(doc_snd, output);
  return output;
}

void reconnect() {
  while(client.state() != MQTT_CONNECTED) {
    if(client.connect("TiotGroup1")) {
      client.subscribe((base_topic + String("/led")).c_str());
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(9600);
  while(!Serial){
    Serial.print("Serial andato");
  }
  
  pinMode(LED_PIN, OUTPUT); 
  // Temperature
  pinMode(TEMP_PIN, INPUT);
  while (status != WL_CONNECTED){
    Serial.println("Attempting to connect to SSID: ");
    Serial.println(SECRET_SSID);
    status = WiFi.begin(SECRET_SSID, SECRET_PASS);
    delay(10000);
  }
}

void loop() {
  if(client.state() != MQTT_CONNECTED) reconnect();
  
  static unsigned long lastMsg = 0;
  if (millis() - lastMsg > 5000) {  
    lastMsg = millis();
    float temp = tempConverter(analogRead(TEMP_PIN));
    client.publish((base_topic + "/temperature").c_str(), senMlEncode("temperature", temp, "Cel").c_str());
  }
  client.loop();
}
