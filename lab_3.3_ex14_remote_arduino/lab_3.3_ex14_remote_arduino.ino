#include <WiFiNINA.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <ArduinoHttpClient.h>
#include <LiquidCrystal_PCF8574.h>
#include <PDM.h>
#include "arduino_secrets.h"

#define DEBUG 1
#define USERNAME "arduino_group1_ex14"
#define DEVICE_ID "arduino_group1_ex14"
#define BASE_NAME "ArduinoGroup1Ex14"

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
const String PRESENCE_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/presence";
const String NOISE_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/noise";

const String LED_COMMAND_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/commands/led";
const String FAN_COMMAND_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/commands/fan";
const String HEATER_COMMAND_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/commands/heater";
const String LCD_COMMAND_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/commands/lcd";

const String LED_FEEDBACK_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/feedback/led";
const String FAN_FEEDBACK_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/feedback/fan";
const String HEATER_FEEDBACK_TOPIC = BASE_TOPIC + "/" + String(DEVICE_ID) + "/feedback/heater";

const int TEMP_PIN = A3;
const int PIR_PIN = 12;
const int GREEN_PIN = 2;
const int HEATER_PIN = A1;
const int FAN_PIN = A2;

const int B = 4275;
const long int R0 = 100000;
const float VCC = 1023.0;
const int SOUND_THRESHOLD = 800;

const unsigned long SENSOR_PERIOD_MS = 10000;
const unsigned long REGISTRATION_RENEWAL_MS = 60000;
const unsigned long PRESENCE_HOLD_MS = 30000;
const unsigned long NOISE_HOLD_MS = 40000;

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

String broker_address = "test.mosquitto.org";
int broker_port = 1883;

int wifi_status = WL_IDLE_STATUS;
unsigned long lastSensorPublish = 0;
unsigned long lastRegistrationRenewal = 0;
unsigned long lastPirPresence = 0;
unsigned long lastNoisePresence = 0;

short sampleBuffer[256];
volatile bool noiseDetected = false;

StaticJsonDocument<1536> doc_snd;
StaticJsonDocument<1024> doc_rec;

WiFiClient mqttWifi;
WiFiClient httpWifi;
PubSubClient client(mqttWifi);
LiquidCrystal_PCF8574 lcd(0x27);

void onPDMdata() {
  int bytesAvailable = PDM.available();
  PDM.read(sampleBuffer, bytesAvailable);
  int samplesRead = bytesAvailable / 2;

  for (int i = 0; i < samplesRead; i++) {
    if (abs(sampleBuffer[i]) > SOUND_THRESHOLD) {
      noiseDetected = true;
      lastNoisePresence = millis();
      break;
    }
  }
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
  HttpClient http(httpWifi, CATALOG_HOST, CATALOG_PORT);

  http.beginRequest();
  http.get(fullPath);
  http.endRequest();

  response = http.responseBody();
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
}

String senmlValue(String name, String unit, float value) {
  doc_snd.clear();
  doc_snd["bn"] = "/sensor/" + ROOM;
  doc_snd["bt"] = millis() / 1000;
  doc_snd["e"][0]["n"] = name;
  doc_snd["e"][0]["u"] = unit;
  doc_snd["e"][0]["v"] = value;
  String output;
  serializeJson(doc_snd, output);
  return output;
}

String senmlBool(String name, bool value) {
  doc_snd.clear();
  doc_snd["bn"] = "/sensor/" + ROOM;
  doc_snd["bt"] = millis() / 1000;
  doc_snd["e"][0]["n"] = name;
  doc_snd["e"][0]["u"] = "boolean";
  doc_snd["e"][0]["bv"] = value;
  String output;
  serializeJson(doc_snd, output);
  return output;
}

String buildDeviceRegistrationPayload() {
  doc_snd.clear();
  doc_snd["id"] = DEVICE_ID;
  doc_snd["description"] = "Arduino v2 for SW exercise 14: temperature, presence, noise, fan, heater, lcd";
  doc_snd["endpoint"] = WiFi.localIP().toString();
  doc_snd["mqtt"]["ip"] = broker_address;
  doc_snd["mqtt"]["port"] = broker_port;

  doc_snd["mqtt"]["pub_topics"][0] = TEMPERATURE_TOPIC;
  doc_snd["mqtt"]["pub_topics"][1] = PRESENCE_TOPIC;
  doc_snd["mqtt"]["pub_topics"][2] = NOISE_TOPIC;
  doc_snd["mqtt"]["pub_topics"][3] = LED_FEEDBACK_TOPIC;
  doc_snd["mqtt"]["pub_topics"][4] = FAN_FEEDBACK_TOPIC;
  doc_snd["mqtt"]["pub_topics"][5] = HEATER_FEEDBACK_TOPIC;

  doc_snd["mqtt"]["sub_topics"][0] = LED_COMMAND_TOPIC;
  doc_snd["mqtt"]["sub_topics"][1] = FAN_COMMAND_TOPIC;
  doc_snd["mqtt"]["sub_topics"][2] = HEATER_COMMAND_TOPIC;
  doc_snd["mqtt"]["sub_topics"][3] = LCD_COMMAND_TOPIC;

  doc_snd["resources"][0] = "temperature";
  doc_snd["resources"][1] = "presence";
  doc_snd["resources"][2] = "noise";
  doc_snd["resources"][3] = "led";
  doc_snd["resources"][4] = "fan";
  doc_snd["resources"][5] = "heater";
  doc_snd["resources"][6] = "lcd";
  doc_snd["time"] = millis();

  String payload;
  serializeJson(doc_snd, payload);
  return payload;
}

void publishDeviceProfile(String topic) {
  String payload = buildDeviceRegistrationPayload();
  client.publish(topic.c_str(), payload.c_str(), false);
  if (DEBUG) {
    Serial.print("[MQTT] Device profile published on ");
    Serial.println(topic);
  }
}

void publishFeedback(String topic, String name, int value, String unit) {
  String payload = senmlValue(name, unit, value);
  client.publish(topic.c_str(), payload.c_str());
}

void displayMessage(String message) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(message.substring(0, 16));
  if (message.length() > 16) {
    lcd.setCursor(0, 1);
    lcd.print(message.substring(16, 32));
  }
  Serial.print("[LCD] ");
  Serial.println(message);
}

void applyCommand(String topic, JsonDocument& doc) {
  JsonObject event = doc["e"][0];
  const char* name = event["n"];

  if (topic == LED_COMMAND_TOPIC || String(name) == "led") {
    int value = event["v"].as<int>();
    digitalWrite(GREEN_PIN, value ? HIGH : LOW);
    publishFeedback(LED_FEEDBACK_TOPIC, "led", value, "bool");
  } else if (topic == FAN_COMMAND_TOPIC || String(name) == "fan") {
    int value = constrain(event["v"].as<int>(), 0, 255);
    analogWrite(FAN_PIN, value);
    publishFeedback(FAN_FEEDBACK_TOPIC, "fan", value, "PWM");
  } else if (topic == HEATER_COMMAND_TOPIC || String(name) == "heater") {
    int value = constrain(event["v"].as<int>(), 0, 255);
    analogWrite(HEATER_PIN, value);
    publishFeedback(HEATER_FEEDBACK_TOPIC, "heater", value, "PWM");
  } else if (topic == LCD_COMMAND_TOPIC || String(name) == "lcd") {
    const char* text = event["vs"] | "";
    displayMessage(String(text));
  }
}

void callback(char* topic, byte* payload, unsigned int length) {
  doc_rec.clear();
  DeserializationError err = deserializeJson(doc_rec, payload, length);
  if (err) {
    Serial.print("[MQTT] JSON parse failed: ");
    Serial.println(err.c_str());
    return;
  }

  String topicString = String(topic);
  if (topicString == ACK_DEVICE_TOPIC) {
    Serial.println("[Catalog ACK]");
    return;
  }
  applyCommand(topicString, doc_rec);
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
      client.subscribe(FAN_COMMAND_TOPIC.c_str());
      client.subscribe(HEATER_COMMAND_TOPIC.c_str());
      client.subscribe(LCD_COMMAND_TOPIC.c_str());
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
  pinMode(HEATER_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);

  lcd.begin(16, 2);
  lcd.setBacklight(128);
  lcd.home();
  lcd.clear();
  lcd.print("Ex14 booting");

  while (wifi_status != WL_CONNECTED) {
    Serial.print("Attempting to connect to SSID: ");
    Serial.println(ssid);
    wifi_status = WiFi.begin(ssid, pass);
    delay(10000);
  }

  Serial.print("Connected with IP address: ");
  Serial.println(WiFi.localIP());

  PDM.onReceive(onPDMdata);
  if (!PDM.begin(1, 20000)) {
    Serial.println("Failed to start PDM. Noise publishing will stay false.");
  }

  retrieveCatalogBroker();
  client.setServer(broker_address.c_str(), broker_port);
  client.setCallback(callback);
  client.setBufferSize(1536);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  unsigned long now = millis();
  if (digitalRead(PIR_PIN) == HIGH) {
    lastPirPresence = now;
  }

  bool pirPresence = (now - lastPirPresence) < PRESENCE_HOLD_MS;
  bool noisePresence = noiseDetected && ((now - lastNoisePresence) < NOISE_HOLD_MS);
  if ((now - lastNoisePresence) >= NOISE_HOLD_MS) {
    noiseDetected = false;
  }

  if (now - lastSensorPublish >= SENSOR_PERIOD_MS) {
    lastSensorPublish = now;

    float temperature = tempConverter(analogRead(TEMP_PIN));
    client.publish(TEMPERATURE_TOPIC.c_str(), senmlValue("temperature", "Celsius", temperature).c_str());
    client.publish(PRESENCE_TOPIC.c_str(), senmlBool("presence", pirPresence || noisePresence).c_str());
    client.publish(NOISE_TOPIC.c_str(), senmlBool("noise", noisePresence).c_str());

    if (DEBUG) {
      Serial.print("[Sensors] T=");
      Serial.print(temperature);
      Serial.print(" presence=");
      Serial.print(pirPresence || noisePresence);
      Serial.print(" noise=");
      Serial.println(noisePresence);
    }
  }

  if (now - lastRegistrationRenewal >= REGISTRATION_RENEWAL_MS) {
    lastRegistrationRenewal = now;
    publishDeviceProfile(REFRESH_DEVICE_TOPIC);
  }

  delay(100);
}
