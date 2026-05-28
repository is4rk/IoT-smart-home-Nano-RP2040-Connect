#include <WiFiNINA.h>
#include "arduino_secrets.h"

#define BASE_NAME "ArduinoGroup1" 
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

void process(WiFiClient client){
  String req_type = client.readStringUntil(' ');
  req_type.trim();
  String url = client.readStringUntil(' ');
  url.trim();
  if(url.startsWith("/led/")){
    String led_val=url.substring(5);
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
  else if(url.startsWith("/temperature/")){
    int a = analogRead(TEMP_PIN);
    temp = tempConverter(a); 
    printResponse(client, 200, senMlEncode("temperature", temp));
  }
  else{
    printResponse(client, 404,"");
  }
}


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

// void toggleStatus(int status){
//   if(status == LOW){
//     greenLedState = HIGH;
//   }
//   else{
//     greenLedState = LOW;
//   }
// }
float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
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



  Serial.print("Connected with IP address: ");
  Serial.print(WiFi.localIP());

  server.begin();
}

void loop() {
  // put your main code here, to run repeatedly:
  WiFiClient client = server.available();
  if(client){
    process(client);
    client.stop();
  }
  delay(50);
}


