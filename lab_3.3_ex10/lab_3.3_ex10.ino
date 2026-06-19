#include <WiFiNINA.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <math.h>
#include "arduino_secrets.h"
// EXERCISE 10
#define DEBUG 1

// =====================
// Team / device settings
// =====================
#define USERNAME "arduino"
#define DEVICE_ID "arduino_group1"
#define BASE_NAME "ArduinoGroup1"

const String GROUP = "group1";
const String BASE_TOPIC = "tiot/" + GROUP + "/catalog";

// MQTT topics used by the Catalog
const String REGISTRATION_DEVICES_TOPIC = BASE_TOPIC + "/devices/registration";
const String REFRESH_DEVICE_TOPIC      = BASE_TOPIC + "/devices/refresh";
const String ACK_DEVICE_TOPIC          = BASE_TOPIC + "/devices/ack/" + DEVICE_ID;
const String LOG_TOPIC                 = "tiot/" + GROUP + "/log";

// Arduino application topics communicated to the Catalog
const String TEMP_TOPIC         = BASE_TOPIC + "/arduino/temperature";
const String LED_COMMAND_TOPIC  = BASE_TOPIC + "/arduino/command/led";
const String LED_FEEDBACK_TOPIC = BASE_TOPIC + "/arduino/feedback/led";

// =====================
// Catalog REST settings
// =====================
const char CATALOG_HOST[] = "10.120.246.215";
const int  CATALOG_PORT = 8080;
const String CATALOG_BASE_PATH = "/catalog";

// =====================
// Pins
// =====================
const int TEMP_PIN = A1;
const int GREEN_PIN = 2;

// =====================
// Broker data. Overwritten after GET.
// =====================
String broker_address = "test.mosquitto.org";
int broker_port = 1883;

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

// Temperature conv const
const int B = 4275;
const long int R0 = 100000;
const float VCC = 1023.0;

// Timers
const unsigned long TEMP_PERIOD_MS = 10000;
const unsigned long REGISTRATION_RENEWAL_MS = 60000;
unsigned long lastTemperaturePublish = 0;
unsigned long lastRegistrationRenewal = 0;

// JSON buffers
StaticJsonDocument<1024> doc_snd;
StaticJsonDocument<1024> doc_rec;

WiFiClient wifi;
WiFiClient http;
PubSubClient client(wifi);
int status = WL_IDLE_STATUS;

// =====================
// Utility functions
// =====================
String senMlEncode(String res, float v, String unit) { 
  doc_snd.clear();
  doc_snd["bn"] = BASE_NAME;
  doc_snd["e"][0]["t"] = int(millis() / 1000);
  doc_snd["e"][0]["n"] = res;
  doc_snd["e"][0]["v"] = v;
  doc_snd["e"][0]["u"] = unit;

  String output;
  serializeJson(doc_snd, output);
  return output;
}

String ledFeedbackEncode(int ledValue) {
  doc_snd.clear();
  doc_snd["bn"] = BASE_NAME;
  doc_snd["e"][0]["t"] = int(millis() / 1000);
  doc_snd["e"][0]["n"] = "led";
  doc_snd["e"][0]["v"] = ledValue;
  doc_snd["e"][0]["u"] = "bool";

  String output;
  serializeJson(doc_snd, output);
  return output;
}

float tempConverter(int a) {
  if (a <= 0) {
    return NAN;
  }
  float R = ((VCC / (float)a) - 1.0) * R0;
  float T = 1.0 / ((log(R / (float)R0) / (float)B) + (1.0 / 298.15));
  return T - 273.15;
}

String httpGET(String path) {
  String response = "";
  String fullPath = CATALOG_BASE_PATH + path;

  if (DEBUG) {
    Serial.print("[REST] GET http://");
    Serial.print(CATALOG_HOST);
    Serial.print(":");
    Serial.print(CATALOG_PORT);
    Serial.println(fullPath);
  }

  if (!http.connect(CATALOG_HOST, CATALOG_PORT)) {
    Serial.println("[REST] Connection to Catalog failed");
    return "";
  }

  http.print(String("GET ") + fullPath + " HTTP/1.1\r\n" +
             "Host: " + CATALOG_HOST + "\r\n" +
             "Connection: close\r\n\r\n");

  unsigned long start = millis();
  while (http.connected() || http.available()) {
    while (http.available()) {
      response += (char)http.read();
    }
    if (millis() - start > 5000) {
      Serial.println("[REST] Timeout while reading Catalog response");
      break;
    }
  }
  http.stop();

  int bodyStart = response.indexOf("\r\n\r\n");
  if (bodyStart >= 0) {
    return response.substring(bodyStart + 4);
  }
  return response;
}

void retrieveCatalogInformationViaREST() {
  // Retrieves broker conf from the Catalog.
  String brokerBody = httpGET("/broker");
  if (brokerBody.length() > 0) {
    StaticJsonDocument<256> brokerDoc;
    DeserializationError err = deserializeJson(brokerDoc, brokerBody);
    if (!err) {
      if (brokerDoc.containsKey("ip")) {
        broker_address = brokerDoc["ip"].as<String>();
      }
      if (brokerDoc.containsKey("port")) {
        broker_port = brokerDoc["port"].as<int>();
      }
      Serial.print("[Catalog] MQTT broker: ");
      Serial.print(broker_address);
      Serial.print(":");
      Serial.println(broker_port);
    } else {
      Serial.print("[Catalog] Cannot parse /broker response: ");
      Serial.println(err.c_str());
    }
  }

  // 2) Retrieve current available devices/services
  String devicesBody = httpGET("/devices");
  if (DEBUG && devicesBody.length() > 0) {
    Serial.print("[Catalog] Current devices: ");
    Serial.println(devicesBody);
  }

  String servicesBody = httpGET("/services");
  if (DEBUG && servicesBody.length() > 0) {
    Serial.print("[Catalog] Current services: ");
    Serial.println(servicesBody);
  }
}

String buildDeviceRegistrationPayload() {
  doc_snd.clear();

  doc_snd["id"] = DEVICE_ID;
  doc_snd["description"] = "Arduino temperature sensor and LED actuator - Exercise 10";
  doc_snd["endpoint"] = WiFi.localIP().toString();

  doc_snd["mqtt"]["ip"] = broker_address;
  doc_snd["mqtt"]["port"] = broker_port;
  doc_snd["mqtt"]["pub_topics"][0] = TEMP_TOPIC;
  doc_snd["mqtt"]["pub_topics"][1] = LED_FEEDBACK_TOPIC;
  doc_snd["mqtt"]["sub_topics"][0] = LED_COMMAND_TOPIC;

  doc_snd["resources"][0] = "temperature";
  doc_snd["resources"][1] = "led";

  String payload;
  serializeJson(doc_snd, payload);
  return payload;
}

void publishDeviceProfile(String topic) {
  String payload = buildDeviceRegistrationPayload();

  if (DEBUG) {
    Serial.print("[MQTT] Publishing device profile on ");
    Serial.println(topic);
    Serial.println(payload);
  }

  bool ok = client.publish(topic.c_str(), payload.c_str());
  if (!ok) {
    Serial.println("[MQTT] Device profile publish failed. Check MQTT buffer size and connection.");
  }
}

void applyLedCommand(int value) {
  if (value == 1) {
    digitalWrite(GREEN_PIN, HIGH);
    Serial.println("[LED] ON");
  } else {
    digitalWrite(GREEN_PIN, LOW);
    Serial.println("[LED] OFF");
  }

  String feedback = ledFeedbackEncode(value);
  client.publish(LED_FEEDBACK_TOPIC.c_str(), feedback.c_str());
}

// =====================
// MQTT callback
// =====================
void callback(char* topic, byte* payload, unsigned int length) {
  String topicString = String(topic);

  if (length >= 512) {
    Serial.println("[MQTT] Message too long, ignored");
    return;
  }

  char message[512];
  for (unsigned int i = 0; i < length; i++) {
    message[i] = (char)payload[i];
  }
  message[length] = '\0';

  if (DEBUG) {
    Serial.print("[MQTT] Message arrived on topic: ");
    Serial.println(topicString);
    Serial.print("[MQTT] Payload: ");
    Serial.println(message);
  }

  // ACK from MQTTCatalogBridge.
  if (topicString == ACK_DEVICE_TOPIC) {
    Serial.print("[Catalog ACK] ");
    Serial.println(message);
    return;
  }

  // LED command.
  if (topicString == LED_COMMAND_TOPIC) {
    doc_rec.clear();
    DeserializationError err = deserializeJson(doc_rec, message);
    if (err) {
      Serial.print("[MQTT] JSON parse failed: ");
      Serial.println(err.c_str());
      return;
    }

    int value = -1;

    // SenML command {"bn":"...","e":[{"n":"led","v":1}]}
    if (doc_rec.containsKey("e")) {
      const char* commandName = doc_rec["e"][0]["n"];
      if (commandName != NULL && strcmp(commandName, "led") == 0) {
        value = doc_rec["e"][0]["v"].as<int>();
      }
    }

    // {"led":1}
    if (value == -1 && doc_rec.containsKey("led")) {
      value = doc_rec["led"].as<int>();
    }

    if (value == 0 || value == 1) {
      applyLedCommand(value);
    } else {
      Serial.println("[MQTT] Invalid LED command. Use value 0 or 1.");
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("[MQTT] Attempting connection to ");
    Serial.print(broker_address);
    Serial.print(":");
    Serial.println(broker_port);

    if (client.connect(USERNAME)) {
      Serial.println("[MQTT] Connected");

      client.subscribe(LED_COMMAND_TOPIC.c_str());
      client.subscribe(ACK_DEVICE_TOPIC.c_str());

      Serial.print("[MQTT] Subscribed to LED command topic: ");
      Serial.println(LED_COMMAND_TOPIC);
      Serial.print("[MQTT] Subscribed to Catalog ACK topic: ");
      Serial.println(ACK_DEVICE_TOPIC);

      // init MQTT reg on the Catalog bridge.
      publishDeviceProfile(REGISTRATION_DEVICES_TOPIC);
      lastRegistrationRenewal = millis();
    } else {
      Serial.print("[MQTT] Connection failed, rc=");
      Serial.print(client.state());
      Serial.println(". Retrying in 5 seconds.");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(9600);
  while (!Serial);
  Serial.println("Serial connected");

  pinMode(TEMP_PIN, INPUT);
  pinMode(GREEN_PIN, OUTPUT);
  digitalWrite(GREEN_PIN, LOW);

  while (status != WL_CONNECTED) {
    Serial.print("Attempting to connect to SSID: ");
    Serial.println(ssid);
    status = WiFi.begin(ssid, pass);
    delay(10000);
  }

  Serial.print("Connected with IP address: ");
  Serial.println(WiFi.localIP());

  retrieveCatalogInformationViaREST();

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

  // Temperature pub evry 10 sec
  if (now - lastTemperaturePublish >= TEMP_PERIOD_MS) {
    lastTemperaturePublish = now;

    float temperature = tempConverter(analogRead(TEMP_PIN));
    String payload = senMlEncode("temperature", temperature, "Cel");

    if (DEBUG) {
      Serial.print("[MQTT] Publishing temperature on ");
      Serial.println(TEMP_TOPIC);
      Serial.println(payload);
    }

    client.publish(TEMP_TOPIC.c_str(), payload.c_str());
    client.publish(LOG_TOPIC.c_str(), payload.c_str());
  }

  // Registration refresh
  if (now - lastRegistrationRenewal >= REGISTRATION_RENEWAL_MS) {
    lastRegistrationRenewal = now;
    publishDeviceProfile(REFRESH_DEVICE_TOPIC);
  }

  delay(100);
}
