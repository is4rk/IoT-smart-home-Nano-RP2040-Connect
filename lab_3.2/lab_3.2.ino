#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>
#include "arduino_secrets.h"

#define BASE_NAME "ArduinoGroup1"
#define HOST_NAME "172.20.10.6"
#define PORT_NUMB 9966

// Pins:
int GREEN_PIN = 2;
const int TEMP_PIN = A1;

// Server (pc) IP address:
char server_address[] = HOST_NAME;
int server_port = PORT_NUMB;

// Temperature conversion constants:
const int B = 4275;
const long int R0 = 100000;
const float VCC = 1023;
float temp = 0;

// WiFi credentials:
char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

// WiFi declarations:
int status = WL_IDLE_STATUS;
WiFiServer server(80); // Server open on port 80

// HttpClient declaration starting from a WiFiNina client.
WiFiClient wifi;
HttpClient client = HttpClient(wifi, server_address, server_port);

// To make a flexible SenML Encoder function, we define a generic type T to pass
// and correctly attach whatever type of value we need to use
template <typename T>
// Manual json SenML string encoder:
String senMlEncode(String name, T value){
  String body = "{";
    body += (String("\"bn\":\"") + BASE_NAME + "\",");
    body += "\"e\":[{";
    body += "\"n\":\"" + name + "\",";
    body += "\"t\":" + String(millis()) + ",";
    body += "\"v\":" + String(value) + ",";
    name == "led" ? body += "\"u\":\"Boolean\"" : body += "\"u\":\"Cel\"";
    body += "}]}";
  return body;
}

// Temperature sensor to Cel conversion function:
float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
}

// POST HTTP request function via HttpClient
int POST(String payload){
  client.beginRequest();
  // request: POST [host]:[port]/log
  client.post("/log");
  // Additional body informations in the header
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", payload.length());
  // Body start:
  client.beginBody();
  client.print(payload);
  client.endRequest();
  // Return response status code
  return client.responseStatusCode();
}

// GET HTTP request function via HttpClient
// Using C++ references to return response body out of the function without using return
int GET(String& response){
  client.beginRequest();
  // request: GET [host]:[port]/log
  client.get("/log");
  // GET: no body and related informations 
  client.endRequest(); 
  // Wait for status code
  int status = client.responseStatusCode();
  // Read response body (can't call responseBody() before status code)
  response = client.responseBody();
  // Return response status code
  return status;
}

// Setup:
void setup() {
  // Serial start:
  Serial.begin(9600);
  while(!Serial);
  Serial.println("Serial connected");
  // Temperature pin mode:
  pinMode(TEMP_PIN, INPUT);
  // WiFi connection start:
  while (status != WL_CONNECTED){
    pinMode(GREEN_PIN, OUTPUT);
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
  String response;
  int a = analogRead(TEMP_PIN);
  temp = tempConverter(a); 

  // Encode temperature in SenML, then send it with an HTTP POST request
  String payload = senMlEncode("temperature", temp);
  Serial.print("POST response code: ");
  Serial.println(POST(payload));

  // Ask stored data on server with a HTTP GET request, then save the response
  // body in a String
  Serial.print("GET response code: ");
  Serial.println(GET(response));
  Serial.println("Response body: ");
  Serial.println(response);
  
  // Wait to not overload
  delay(2000);
}
