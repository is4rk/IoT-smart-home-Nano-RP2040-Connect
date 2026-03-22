#include <LiquidCrystal_PCF8574.h>
#include <MBED_RPi_Pico_TimerInterrupt.h> 
#include <PDM.h>
#include <Scheduler.h>
LiquidCrystal_PCF8574 lcd(0x27);
const int RLED_PIN = A1;
const int GLED_PIN = 2;
const int FAN_PIN = A2;
const int PIR_PIN = 12;
const int TEMP_PIN = A3;
const int B = 4275;
const long int R0 = 100000;
const float VCC =1023;
float temp=0;
float fanSpeed=0;
float heaterIntensity=0;
//no persons
const int MAX_TEMP = 30;
const int MIN_TEMP = 25;
const int MAX_TEMP_HEATER = 20;
const int MIN_TEMP_HEATER = 15;
int lcd_state=1;
//persons, TO BE CHANGED
const int MAX_TEMP_PERSvoid setup() {
  // put your setup code here, to run once:

}

void loop() {
  // put your main code here, to run repeatedly:

}
= 25;
const int MIN_TEMP_PERS = 20;
const int MAX_TEMP_HEATER_PERS= 10;
const int MIN_TEMP_HEATER_PERS= 5;

volatile int pir_detects_person =0;
const int timeout_PIR = 3000;
//MIC
volatile int mic_detects_person =1;

const int timeout_MIC = 100;
int local_pdp=0;
int local_mdp=0;
MBED_RPI_PICO_Timer ITimer1(1);
MBED_RPI_PICO_Timer ITimer2(1);
MBED_RPI_PICO_Timer ITimer3(2);

int n_sound_events = 0;
const int timout_LCD =5000;
//const int sound_threshold =;
//const int sound_interval = ;
//const int timeout_sound = ;
short sampleBuffer[256];
int ringBuffer[16];
int indexRB = 0;
volatile int samplesRead;

void onPDMdata(){

  int bytesAvailable = PDM.available();
  
  PDM.read(sampleBuffer, bytesAvailable);

  samplesRead = bytesAvailable / 2;

  if(samplesRead){
    for(int i = 0; i < samplesRead; i++){
      if(abs(sampleBuffer[i])>800) //measured with fan on max speed 
        // Serial.println(sampleBuffer[i]);
        microphoneEvent();
    }
    samplesRead = 0;
  }

}

void timerDonePir(uint alarm_num){
  TIMER_ISR_START(alarm_num);
  //se scade il timer, resetta le persone presenti nella stanza
  pir_detects_person=0;
  local_pdp = 0;
  TIMER_ISR_END(alarm_num);
}
void timerDoneMic(uint alarm_num){
  TIMER_ISR_START(alarm_num);
  //se scade il timer, resetta le persone presenti nella stanza
  mic_detects_person=0;
  local_mdp = 0;
  TIMER_ISR_END(alarm_num);
}void setup() {
  // put your setup code here, to run once:

}

void loop() {
  // put your main code here, to run repeatedly:

}




void foundPresencePir(){
  pir_detects_person=1;
  ITimer1.setInterval(timeout_PIR * 1000 , timerDonePir); 
}

int tempHeaterIntensity(float x, int min, int max ){
  
  if( x < min){
    return 255;
  }
  if(x > max){void setup() {
  // put your setup code here, to run once:

}

void loop() {
  // put your main code here, to run repeatedly:

}

    return 0; 
  }

  float HEATER_intensity = (255)* (1- (x-min)/(max - min));
  return ( int ) HEATER_intensity;

}

int tempFanSpeed(float x, int min, int max ){
  if( x < min){
    return 0;
  }
  if(x > max){
    return 255; 
  }  
  
  float FAN_speed = (255)* (x-min)/(max - min);

  return (int) FAN_speed;
}

float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
}

void resetMicrophoneTimer(){
  ITimer2.setInterval(timeout_MIC * 1000 , timerDoneMic); 
}

void microphoneEvent(){
  ringBuffer[indexRB % 16] = millis();
  indexRB++;

  if(indexRB>=9 && (ringBuffer[(indexRB-1) % 16]-ringBuffer[(indexRB-10) % 16])<60){
    mic_detects_person=1;
    resetMicrophoneTimer();
  }
}
void lcdChangeState(uint alarm_num){
  TIMER_ISR_START(alarm_num);
  

  lcd_state =  !lcd_state;
  ITimer3.setInterval(timout_LCD * 1000 , lcdChangeState); //appena scade il timer, resetta il numero di persone
  TIMER_ISR_END(alarm_num);

}
void printLcd(){
  //g.
  if(lcd_state){
    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("T:");
    lcd.print(temp);
    lcd.print(" Pres:");
    lcd.print((int)(local_mdp));
    lcd.setCursor(0,1);
    lcd.print("AC:");
    lcd.print((int) (fanSpeed/255));
    lcd.print("% HT:");
    lcd.print((int)(heaterIntensity/255));
    lcd.print("%");
  }
  else{
    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("AC m:");
    lcd.print(local_pdp || local_mdp ? MIN_TEMP_PERS : MIN_TEMP);
    lcd.print(" M:");
    lcd.print(local_pdp || local_mdp ? MAX_TEMP_PERS : MAX_TEMP);
    lcd.setCursor(0,1);
    lcd.print("HT m:");
    lcd.print(local_pdp || local_mdp ? MIN_TEMP_HEATER_PERS : MIN_TEMP_HEATER);
    lcd.print(" M:");
    lcd.print(local_pdp || local_mdp ?  MAX_TEMP_HEATER_PERS : MAX_TEMP_HEATER);
  }
}

void setup() {
  //PIN SETUP
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  //pinMode(PIR_PIN, INPUT);
  pinMode(TEMP_PIN, INPUT);
  //LCD SETUP
  lcd.begin(16,2);
  lcd.setBacklight(128);
  lcd.home();
  lcd.clear();
  // lcd.print("Temperature:");
  //c.
  attachInterrupt(digitalPinToInterrupt(PIR_PIN), foundPresencePir, CHANGE);
  ITimer1.setInterval(timeout_PIR * 1000 , timerDonePir); //appena scade il timer, resetta il numero di persone
  
  Serial.begin(9600);
  if(!Serial){
    Serial.println("Starting...");
  }

  //d.
  PDM.onReceive(onPDMdata);
  if(!PDM.begin(1,20000)){
    Serial.println("Failed to start PDM!");
    while(1);
  }
  ITimer2.setInterval(timeout_MIC * 1000 , timerDoneMic); //appena scade il timer, resetta il numero di persone
  Scheduler.startLoop(loop2);

  //g.
  ITimer3.setInterval(timout_LCD * 1000 , lcdChangeState); //appena scade il timer, resetta il numero di persone

}

void loop() {
  // put your main code here, to run repeatedly:
  // a. si prende la temperatura su x, la si converte in temp, e la si passa a tempFanSpeed
  int x = analogRead(TEMP_PIN);
  temp = tempConverter(x);
  // lcd.setCursor(12, 0); //per sovrascrivere ogni volta
  // lcd.print(temp);
  if(mic_detects_person||pir_detects_person){
    fanSpeed=tempFanSpeed(temp, MIN_TEMP_PERS, MAX_TEMP_PERS);
  }
  else{
        fanSpeed=tempFanSpeed(temp, MIN_TEMP, MAX_TEMP);
  }
  analogWrite(FAN_PIN, fanSpeed);

  delay(500); //da cambiare giusto per il test
  // b. 
  if(mic_detects_person||pir_detects_person){
    heaterIntensity= tempHeaterIntensity(temp, MIN_TEMP_HEATER_PERS , MAX_TEMP_HEATER_PERS);
  }
  else{
   heaterIntensity=tempHeaterIntensity(temp, MIN_TEMP_HEATER , MAX_TEMP_HEATER);
  }
  analogWrite(RLED_PIN, heaterIntensity);

  //c.
  noInterrupts();
  local_pdp = pir_detects_person;
  local_mdp = mic_detects_person;
  interrupts();
  // Serial.print("Total people count: ");
  // Serial.println(a);
  printLcd();
  delay(200);

}

//Serial listen loop
void loop2(){
  //h.
  yield();
}
