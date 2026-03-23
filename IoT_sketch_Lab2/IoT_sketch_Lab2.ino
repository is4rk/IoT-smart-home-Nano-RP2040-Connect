// includes
#include <LiquidCrystal_PCF8574.h>
#include <MBED_RPi_Pico_TimerInterrupt.h> 
#include <PDM.h>
#include <Scheduler.h>

  /*************/
 /* CONSTANTS */
/*************/
// Pin definitions
const int RLED_PIN = A1;
const int GLED_PIN = 2;
const int FAN_PIN = A2;
const int PIR_PIN = 12;
const int TEMP_PIN = A3;
// Temperature sensor constants
const int B = 4275;
const long int R0 = 100000;
const float VCC = 1023;
// Temperatures:
// No person detected
const int MAX_TEMP = 30;
const int MIN_TEMP = 25;
const int MAX_TEMP_HEATER = 20;
const int MIN_TEMP_HEATER = 15;
// Person detected
const int MAX_TEMP_PERS= 25;
const int MIN_TEMP_PERS = 20;
const int MAX_TEMP_HEATER_PERS= 10;
const int MIN_TEMP_HEATER_PERS= 5;
// Timeout definitions
const int TIMEOUT_MIC = 100;
const int TIMEOUT_PIR = 3000;
const int TIMEOUT_LCD = 5000;
// Other constants
const int RB_SIZE = 16;

//const int sound_threshold =;
//const int sound_interval = ;
//const int timeout_sound = ;

  /*************/
 /* VARIABLES */
/*************/
// Volatile variables
volatile int pir_detects_person = 0;
volatile int mic_detects_person = 0;
volatile int samplesRead;
// Variables
int n_sound_events = 0;
int indexRB = 0;
float temp=0;
float fanSpeed=0;
float heaterIntensity=0;
int local_pdp=0;
int local_mdp=0;
int lcd_state=1;

  /****************/
 /* DECLARATIONS */
/****************/
// Buffers
short sampleBuffer[256];
int ringBuffer[RB_SIZE];
// Display screen
LiquidCrystal_PCF8574 lcd(0x27);
// Timer interrupts
MBED_RPI_PICO_Timer ITimer1(1);
MBED_RPI_PICO_Timer ITimer2(1);
MBED_RPI_PICO_Timer ITimer3(2);

  /*************/
 /* FUNCTIONS */
/*************/

// Microphone data ISR handler
void onPDMdata(){
  // 
  int bytesAvailable = PDM.available();
  
  PDM.read(sampleBuffer, bytesAvailable);
  samplesRead = bytesAvailable / 2;

  if(samplesRead){
    for(int i = 0; i < samplesRead; i++){
      if(abs(sampleBuffer[i])>800) {  //measured with fan on max speed 
        ringBuffer[indexRB % RB_SIZE] = millis();
        indexRB++;
        
        // If there are at least 10 data in the ring buffer and ...
        if(indexRB >= 9 && (ringBuffer[(indexRB-1) % RB_SIZE]- ringBuffer[(indexRB-10) % RB_SIZE]) < 60){
          mic_detects_person = 1;
          resetMicrophoneTimer();
        }
      }
    samplesRead = 0;
    }
  }
}

void timerDonePir(uint alarm_num){
  TIMER_ISR_START(alarm_num);
  //se scade il timer, resetta le persone presenti nella stanza
  pir_detects_person = 0;
  // local_pdp = 0;
  TIMER_ISR_END(alarm_num);
}

void timerDoneMic(uint alarm_num){
  TIMER_ISR_START(alarm_num);
  //se scade il timer, resetta le persone presenti nella stanza
  mic_detects_person = 0;
  // local_mdp = 0;
  TIMER_ISR_END(alarm_num);
}

void foundPresencePir(){
  pir_detects_person=1;
  ITimer1.setInterval(TIMEOUT_PIR * 1000 , timerDonePir); 
}

int heaterIntensityCalc(float temp, float tmin, float tmax){
  if(temp < tmin) return 255;
  if(temp > tmax) return 0; 

  return (int) (255.0 * (1.0 - ((temp - tmin) / (tmax - tmin))));
}

int fanSpeedCalc(float temp, float tmin, float tmax){
  if (temp < tmin) return 0;
  if (temp > tmax) return 255; 

  return (int) (255.0 * (temp - tmin) / (tmax - tmin));
}

float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
}

void resetMicrophoneTimer(){
  ITimer2.setInterval(TIMEOUT_MIC * 1000 , timerDoneMic); 
}


void lcdChangeState(uint alarm_num){
  TIMER_ISR_START(alarm_num);
  lcd_state =  !lcd_state;
  ITimer3.setInterval(TIMEOUT_LCD * 1000 , lcdChangeState); // Redundant? ISR already set, resetting is not useful?
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

  /*********/
 /* SETUP */
/*********/
void setup() {
  // Pin mode setup
  pinMode(RLED_PIN, OUTPUT);
  pinMode(GLED_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT);
  pinMode(TEMP_PIN, INPUT);
  // LCD starting setup
  lcd.begin(16,2);
  lcd.setBacklight(128);
  lcd.home();
  lcd.clear();  
  // Serial starting setup
  Serial.begin(9600);
  if(!Serial){
    Serial.println("Starting...");
  }
  // Microphone starting setup
  PDM.onReceive(onPDMdata);
  if(!PDM.begin(1, 20000)){
    Serial.println("Failed to start PDM!");
    while(1);
  }
  // Scheduler second loop definition
  Scheduler.startLoop(loop2);
  // Interrupts:
  // PIR interrupt
  attachInterrupt(digitalPinToInterrupt(PIR_PIN), foundPresencePir, CHANGE);
  // Timer interrupts start
  ITimer1.setInterval(TIMEOUT_PIR * 1000 , timerDonePir);
  ITimer2.setInterval(TIMEOUT_MIC * 1000 , timerDoneMic);
  ITimer3.setInterval(TIMEOUT_LCD * 1000 , lcdChangeState);
}

  /*********/
 /* LOOPS */
/*********/
// Main loop:
void loop() {
  // a.
  int x = analogRead(TEMP_PIN);
  temp = tempConverter(x);
  
  if(mic_detects_person || pir_detects_person){
    fanSpeed = fanSpeedCalc(temp, (float) MIN_TEMP_PERS, (float) MAX_TEMP_PERS);
  } else {
    fanSpeed = fanSpeedCalc(temp, (float) MIN_TEMP, (float) MAX_TEMP);
  }
  analogWrite(FAN_PIN, fanSpeed);

  // b. 
  if(mic_detects_person || pir_detects_person){
    heaterIntensity = heaterIntensityCalc(temp, (float) MIN_TEMP_HEATER_PERS , (float) MAX_TEMP_HEATER_PERS);
  } else {
    heaterIntensity = heaterIntensityCalc(temp, (float) MIN_TEMP_HEATER , (float) MAX_TEMP_HEATER);
  }
  analogWrite(RLED_PIN, heaterIntensity);

  //c.
  noInterrupts();
  local_pdp = pir_detects_person;
  local_mdp = mic_detects_person;
  interrupts();

  // Lcd screen
  printLcd();
  yield();;
}

//Serial listener loop:
void loop2(){
  //h.
  yield();
}