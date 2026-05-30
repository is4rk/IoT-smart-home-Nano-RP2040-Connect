#include <WiFiNINA.h>
#include "arduino_secrets.h"

#define BASE_NAME "ArduinoGroup1" 

// Pins:
int GREEN_PIN = 2;
const int TEMP_PIN = A1;

// Temperature conversion constants:
const int B = 4275;
const long int R0 = 100000;
const float VCC = 1023;
float temp = 0;

// WiFi credentials:
char ssid[] = SECRET_SSID;
char pass[] = SECRET_PASS;

char ssid[] = "Iphone mio e non tuo";
char pass[] = "638373829";
// WiFi declarations:
int status = WL_IDLE_STATUS;
WiFiServer server(80); // Server open on port 80

// Process incoming connection function:
void process(WiFiClient client){
  //[request type] [url]
  // Get request type:
  String req_type = client.readStringUntil(' ');
  req_type.trim();
  // Get url:
  String url = client.readStringUntil(' ');
  url.trim();
  // TODO: implement more robust checks than these...
  // Check if it is an allowed endpoint:
  if(url.startsWith("/led/")){
    String led_val=url.substring(5);
    Serial.print("Led value: ");
    Serial.println(led_val);
    if(led_val=="0" || led_val=="1"){
      int int_val = led_val.toInt();
      digitalWrite(GREEN_PIN, int_val);
      printResponse(client, 200, senMlEncode("led", int_val));
    }
    else {
      printResponse(client, 404,"");
    }
  }
  else if(url.startsWith("/temperature")){
    int a = analogRead(TEMP_PIN);
    temp = tempConverter(a); 
    printResponse(client, 200, senMlEncode("temperature", temp));
  }
  else{
    printResponse(client, 404,"");
  }
}

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

// Response function
void printResponse(WiFiClient client, int code, String body){
  client.println("HTTP/1.1 " + String(code));
  if(code == 200){
    client.println("Content-type: application/json; charset=utf-8");
    client.println();
    client.println(body);
  }
  else {
    client.println();
  }

}

// Temperature sensor to Cel conversion function:
float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
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
  // WiFi server start:
  server.begin();
}

void loop() {
  // Check connection avaliability:
  WiFiClient client = server.available();
  // Process and terminate connection:
  if(client){
    process(client);
    client.stop();
  }
  // Delay to avoid overloading
  delay(50);
}


