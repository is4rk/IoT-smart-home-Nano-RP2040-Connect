#include <WiFiNINA.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <ArduinoHttpClient.h>
#include "arduino_secrets.h"

#define DEBUG 1
#define USERNAME "arduino_group1_ex13"
#define DEVICE_ID "arduino_group1_ex13"
#define BASE_NAME "ArduinoGroup1Ex13"

// sw lab 3 - exercise 13
// the board reads the physical sensors, publishes SenML measurements on MQTT, and receives MQTT commands for the local LED actuator


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

// pins connected to the sensors and to the LED used as actuator
const int TEMP_PIN = A1;
const int PIR_PIN = 12;
const int GREEN_PIN = 2;

// parameters used by the thermistor equation for the temperature sensor
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

// the MQTT client is created globally, but the broker is configured later after reading it from the catalog
PubSubClient client(mqttWifi);

float tempConverter(int a) {
  // converts the input into a temperature in Celsius
  if (a <= 0) {
    return NAN;
  }

  float R = ((VCC / (float)a) - 1.0) * R0;
  float T = 1.0 / ((log(R / (float)R0) / (float)B) + (1.0 / 298.15));
  return T - 273.15;
}

String httpGET(String path) {
  // sends a GET request to the local catalog and returns the response body with gained infos
  String fullPath = CATALOG_BASE_PATH + path;
  HttpClient http(httpWifi, CATALOG_HOST, CATALOG_PORT);

  // arduinoHttpClient builds the request through begin, method and end calls
  http.beginRequest();
  http.get(fullPath);
  http.endRequest();

  String response = http.responseBody();
  http.stop();
  return response;
}

void retrieveCatalogBroker() {
  // reads the MQTT broker information exposed by the catalog service
  String body = httpGET("/broker");
  StaticJsonDocument<256> brokerDoc;
  DeserializationError err = deserializeJson(brokerDoc, body);

  // the broker is taken from the catalog so the Arduino follows the same configuration used by the components developed in python 
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
  // creates the SenML message used to publish the temperature value
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
  // creates the SenML message used to publish the motion state
  doc_snd.clear();
  doc_snd["bn"] = "/sensor/" + ROOM;
  doc_snd["bt"] = millis() / 1000;
  doc_snd["e"][0]["n"] = "motion";
  doc_snd["e"][0]["u"] = "boolean";
  //   in SenML, boolean values are represented with bv and not v
  doc_snd["e"][0]["bv"] = value;

  String output;
  serializeJson(doc_snd, output);
  return output;
}

String senmlLedFeedback(int value) {
  // creates the SenML feedback message after changing the LED state
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
  // builds the JSON profile used to register this Arduino in the catalog
  doc_snd.clear();

  // device description published to the catalog through the MQTT bridge, according to the message format used in previous exercises
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
  // publishes the current device profile on the selected catalog topic
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
  // it extracts the LED command from the received JSON and applies it locally
  // we expect this command format: {"bn":"RemoteSwitch","e":[{"n":"led","v":1}]}
  JsonObject event = doc["e"][0];
  const char* name = event["n"];

  // messages not referring to the LED are ignored
  if (name == NULL || strcmp(name, "led") != 0) {
    return;
  }

  // the LED is a binary actuator, so all values different from zero are treated as ON
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
  // it  handles MQTT messages received by the aarduino
  String topicString = String(topic);

  // the catalog bridge sends an ACK after processing the registration
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
  //  trying to connect to the MQTT broker until the connection is ready
  while (!client.connected()) {
    Serial.print("[MQTT] Connecting to ");
    Serial.print(broker_address);
    Serial.print(":");
    Serial.println(broker_port);

    if (client.connect(USERNAME)) {
      Serial.println("[MQTT] Connected");

      // subscriptions are restored after each successful connection
      client.subscribe(ACK_DEVICE_TOPIC.c_str());
      client.subscribe(LED_COMMAND_TOPIC.c_str());

      // the device is registered again so the catalog has the current topics
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

  // pin configuration
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

  // broker information is retrieved before configuring the MQTT client
  retrieveCatalogBroker();
  client.setServer(broker_address.c_str(), broker_port);
  client.setCallback(callback);
  // the registration payload is larger than a simple sensor message
  client.setBufferSize(1024);
}

void loop() {
  // keeps MQTT alive and periodically publishes sensor values
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();

  // the PIR signal may be short so by keeping a temporary motion state avoids losing the event between two periodic publications
  if (digitalRead(PIR_PIN) == HIGH) {
    lastMotionSeen = now;
  }
  bool motion = (now - lastMotionSeen) < MOTION_HOLD_MS;

  if (now - lastSensorPublish >= SENSOR_PERIOD_MS) {
    lastSensorPublish = now;

    float temperature = tempConverter(analogRead(TEMP_PIN));

    // sensor events are published by Arduino and the controller receives these values and applies the automation rules
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
    // just refreshing the device
    publishDeviceProfile(REFRESH_DEVICE_TOPIC);
  }

  // we add jus a short pause to limit the frequency but without blocking MQTT for to much
  delay(100);
}
