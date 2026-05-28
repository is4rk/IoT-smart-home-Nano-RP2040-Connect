#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>
#include "arduino_secrets.h"
#define BASE_NAME "ArduinoGroup1" 

char server_address[]= "172.20.10.3";
int server_port = 9966;
const int TEMP_PIN = A1;
const int B = 4275;
const long int R0 = 100000;
const float VCC =1023;
float temp=0;

char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;



int status = WL_IDLE_STATUS;
WiFiServer server(80);

int GREEN_PIN = 2;
int greenLedState = LOW;
WiFiClient wifi;
HttpClient client = HttpClient(wifi, server_adress, server_port);


String senMlEncode(String name, int value){
String body = "{";
  body += (String("\"bn\":\"") + BASE_NAME + "\",");
  body += "\"e\":[{";
  body += "\"n\":\""+name+"\",";
  body += "\"t\":" + String(millis()) + ",";
  body += "\"v\":" + String(value) + ",";
  name=="led" ? body += "\"u\":\"Boolean\"" : body += "\"u\":\"Cel\"";
  body += "}]}";
  return body;
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  while(!Serial){
    Serial.print("Serial andato");
  }
  
  // Temperature
  pinMode(TEMP_PIN, INPUT);
  while (status != WL_CONNECTED){
    pinMode(GREEN_PIN, OUTPUT);
    Serial.println("Attempting to connect to SSID: ");
    Serial.println(ssid);
    status = WiFi.begin(ssid, pass);
    delay(10000);
  }
}

float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
}

void loop() {
  int a = analogRead(TEMP_PIN);
  temp = tempConverter(a); 
  String body = senMlEncode("temperature", temp);
  client.beginRequest();
  client.post("/log");
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Lenght", body.length());
  client.beginBody();
  client.print(body);
  client.endRequest();
  int ret = client.responseStatusCode();
  Serial.print("Response code: ");
  Serial.println(ret)
  delay(2000)
}
