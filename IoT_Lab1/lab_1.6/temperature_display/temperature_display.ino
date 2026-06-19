#include <LiquidCrystal_PCF8574.h>
LiquidCrystal_PCF8574 lcd(0x27);
const int TEMP_PIN = A1;
const int B = 4275;
const long int R0 = 100000;
const float VCC =1023;
float temp=0;

// convertitore da analog a °C secondo le specifiche del sensore
float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
}

void setup() {
  // put your setup code here, to run once:
  //setup iniziale dello schermo
  lcd.begin(16, 2);
  lcd.setBacklight(128);
  lcd.home();
  lcd.clear();
  lcd.print("Temperature:");
  pinMode(TEMP_PIN, INPUT);
}

void loop() {
  // put your main code here, to run repeatedly:
  //controllo temp ogni 3 sec e stampo sullo schermo
  int a = analogRead(TEMP_PIN);
  temp = tempConverter(a);
  lcd.setCursor(12, 0); //per sovrascrivere ogni volta
  lcd.print(temp);
  delay(3000);
}
