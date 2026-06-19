#include <WiFiNINA.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <ArduinoHttpClient.h>
#include "arduino_secrets.h"

#define DEBUG 1
#define USERNAME "arduino_group1_ex13"
#define DEVICE_ID "arduino_group1_ex13"
#define BASE_NAME "ArduinoGroup1Ex13"

// Change this to the LAN IP of the PC running `python main.py`.
const char CATALOG_HOST[] = "10.120.246.215";
const int CATALOG_PORT = 8080;
const String CATALOG_BASE_PATH = "/catalog";

const String GROUP = "group1";
const String ROOM = "kitchen";
const String BASE_TOPIC = "tiot/" + GROUP;

const String REGISTRATION_DEVICES_TOPIC = BASE_TOPIC + "/catalog/devices/registration";
const String REFRESH_DEVICE_TOPIC = BASE_TOPIC + "/catalog/devices/refresh";
const String ACK_DEVICE_TOPIC = BASE_TOPIC + "/catalog/devices/ack/" + String(DEVICE_ID);

const String TEMPERATURE_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/temperature";
const String MOTION_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/motion";
const String LED_COMMAND_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/commands/led";
const String LED_FEEDBACK_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/feedback/led";

const int TEMP_PIN = A1;
const int PIR_PIN = 12;
const int GREEN_PIN = 2;

const int B = 4275;
const long int R0 = 100000;
const float VCC = 1023.0;

const unsigned long SENSOR_PERIOD_MS = 10000;
const unsigned long REGISTRATION_RENEWAL_MS = 60000;
const unsigned long MOTION_HOLD_MS = 30000;

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

String broker_address = "test.mosquitto.org";
int broker_port = 1883;

int wifi_status = WL_IDLE_STATUS;
unsigned long lastSensorPublish = 0;
unsigned long lastRegistrationRenewal = 0;
unsigned long lastMotionSeen = 0;

StaticJsonDocument<1024> doc_snd;
StaticJsonDocument<512> doc_rec;

WiFiClient mqttWifi;
WiFiClient httpWifi;
PubSubClient client(mqttWifi);

float tempConverter(int a) {
  if (a <= 0) {
    return NAN;
  }
  float R = ((VCC / (float)a) - 1.0) * R0;
  float T = 1.0 / ((log(R / (float)R0) / (float)B) + (1.0 / 298.15));
  return T - 273.15;
}

String httpGET(String path) {
  String fullPath = CATALOG_BASE_PATH + path;
  HttpClient http(httpWifi, CATALOG_HOST, CATALOG_PORT);

  http.beginRequest();
  http.get(fullPath);
  http.endRequest();

  String response = http.responseBody();
  http.stop();
  return response;
}

void retrieveCatalogBroker() {
  String body = httpGET("/broker");
  StaticJsonDocument<256> brokerDoc;
  DeserializationError err = deserializeJson(brokerDoc, body);
  if (!err) {
    broker_address = brokerDoc["ip"].as<String>();
    broker_port = brokerDoc["port"].as<int>();
  }

  if (DEBUG) {
    Serial.print("[Catalog] Broker ");
    Serial.print(broker_address);
    Serial.print(":");
    Serial.println(broker_port);
  }
}

String senmlTemperature(float value) {
  doc_snd.clear();
  doc_snd["bn"] = "/sensor/" + ROOM;
  doc_snd["bt"] = millis() / 1000;
  doc_snd["e"][0]["n"] = "temperature";
  doc_snd["e"][0]["u"] = "Celsius";
  doc_snd["e"][0]["v"] = value;

  String output;
  serializeJson(doc_snd, output);
  return output;
}

String senmlMotion(bool value) {
  doc_snd.clear();
  doc_snd["bn"] = "/sensor/" + ROOM;
  doc_snd["bt"] = millis() / 1000;
  doc_snd["e"][0]["n"] = "motion";
  doc_snd["e"][0]["u"] = "boolean";
  doc_snd["e"][0]["bv"] = value;

  String output;
  serializeJson(doc_snd, output);
  return output;
}

String senmlLedFeedback(int value) {
  doc_snd.clear();
  doc_snd["bn"] = BASE_NAME;
  doc_snd["bt"] = millis() / 1000;
  doc_snd["e"][0]["n"] = "led";
  doc_snd["e"][0]["u"] = "bool";
  doc_snd["e"][0]["v"] = value;

  String output;
  serializeJson(doc_snd, output);
  return output;
}

String buildDeviceRegistrationPayload() {
  doc_snd.clear();

  doc_snd["id"] = DEVICE_ID;
  doc_snd["description"] = "Arduino for SW exercise 13: temperature, motion and remote LED command";
  doc_snd["endpoint"] = WiFi.localIP().toString();
  doc_snd["mqtt"]["ip"] = broker_address;
  doc_snd["mqtt"]["port"] = broker_port;

  doc_snd["mqtt"]["pub_topics"][0] = TEMPERATURE_TOPIC;
  doc_snd["mqtt"]["pub_topics"][1] = MOTION_TOPIC;
  doc_snd["mqtt"]["pub_topics"][2] = LED_FEEDBACK_TOPIC;
  doc_snd["mqtt"]["sub_topics"][0] = LED_COMMAND_TOPIC;

  doc_snd["resources"][0] = "temperature";
  doc_snd["resources"][1] = "motion";
  doc_snd["resources"][2] = "led";
  doc_snd["time"] = millis();

  String payload;
  serializeJson(doc_snd, payload);
  return payload;
}

void publishDeviceProfile(String topic) {
  String payload = buildDeviceRegistrationPayload();
  bool ok = client.publish(topic.c_str(), payload.c_str(), false);

  if (DEBUG) {
    Serial.print("[MQTT] Device profile on ");
    Serial.print(topic);
    Serial.print(" result=");
    Serial.println(ok);
  }
}

void applyLedCommand(JsonDocument& doc) {
  JsonObject event = doc["e"][0];
  const char* name = event["n"];
  if (name == NULL || strcmp(name, "led") != 0) {
    return;
  }

  int value = event["v"].as<int>();
  value = value ? 1 : 0;
  digitalWrite(GREEN_PIN, value ? HIGH : LOW);
  client.publish(LED_FEEDBACK_TOPIC.c_str(), senmlLedFeedback(value).c_str());

  if (DEBUG) {
    Serial.print("[LED] ");
    Serial.println(value ? "ON" : "OFF");
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  String topicString = String(topic);

  if (topicString == ACK_DEVICE_TOPIC) {
    Serial.println("[Catalog ACK]");
    return;
  }

  doc_rec.clear();
  DeserializationError err = deserializeJson(doc_rec, payload, length);
  if (err) {
    Serial.print("[MQTT] JSON parse failed: ");
    Serial.println(err.c_str());
    return;
  }

  if (topicString == LED_COMMAND_TOPIC) {
    applyLedCommand(doc_rec);
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("[MQTT] Connecting to ");
    Serial.print(broker_address);
    Serial.print(":");
    Serial.println(broker_port);

    if (client.connect(USERNAME)) {
      Serial.println("[MQTT] Connected");
      client.subscribe(ACK_DEVICE_TOPIC.c_str());
      client.subscribe(LED_COMMAND_TOPIC.c_str());
      publishDeviceProfile(REGISTRATION_DEVICES_TOPIC);
      lastRegistrationRenewal = millis();
    } else {
      Serial.print("[MQTT] Connection failed rc=");
      Serial.println(client.state());
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(9600);
  while (!Serial);

  pinMode(TEMP_PIN, INPUT);
  pinMode(PIR_PIN, INPUT);
  pinMode(GREEN_PIN, OUTPUT);
  digitalWrite(GREEN_PIN, LOW);

  while (wifi_status != WL_CONNECTED) {
    Serial.print("Attempting to connect to SSID: ");
    Serial.println(ssid);
    wifi_status = WiFi.begin(ssid, pass);
    delay(10000);
  }

  Serial.print("Connected with IP address: ");
  Serial.println(WiFi.localIP());

  retrieveCatalogBroker();
  client.setServer(broker_address.c_str(), broker_port);
  client.setCallback(callback);
  client.setBufferSize(1024);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();
  if (digitalRead(PIR_PIN) == HIGH) {
    lastMotionSeen = now;
  }
  bool motion = (now - lastMotionSeen) < MOTION_HOLD_MS;

  if (now - lastSensorPublish >= SENSOR_PERIOD_MS) {
    lastSensorPublish = now;

    float temperature = tempConverter(analogRead(TEMP_PIN));
    client.publish(TEMPERATURE_TOPIC.c_str(), senmlTemperature(temperature).c_str());
    client.publish(MOTION_TOPIC.c_str(), senmlMotion(motion).c_str());

    if (DEBUG) {
      Serial.print("[Sensors] temperature=");
      Serial.print(temperature);
      Serial.print(" motion=");
      Serial.println(motion);
    }
  }

  if (now - lastRegistrationRenewal >= REGISTRATION_RENEWAL_MS) {
    lastRegistrationRenewal = now;
    publishDeviceProfile(REFRESH_DEVICE_TOPIC);
  }

  delay(100);
}
