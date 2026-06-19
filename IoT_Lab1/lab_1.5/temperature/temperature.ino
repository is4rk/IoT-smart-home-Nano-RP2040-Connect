  const int TEMP_PIN = A1;
  const int B = 4275;
  const long int R0 = 100000;
  const float VCC =1023;
  float temp=0;

// formula per convertire da analog a °C
float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
}

void setup() {
  pinMode(TEMP_PIN, INPUT);
  Serial.begin(9600);
  while(!Serial);
    Serial.println("Lab 1.5 starting");
}

void loop() {
  // leggi il valore analogico da temp sens e poi converti
  int a = analogRead(TEMP_PIN);
  temp = tempConverter(a);
  Serial.print("temperature = ");
  Serial.println(temp);
  delay(3000);
}
