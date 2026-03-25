// includes
#include <LiquidCrystal_PCF8574.h>
#include <MBED_RPi_Pico_TimerInterrupt.h> 
#include <PDM.h>
#include <Scheduler.h>

  /*************/
 /* CONSTANTS */
/*************/
// How much to remove from char to get int. ASCII(0) = decimal 49
const int INT_ASCII=48;
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
// Timeout definitions
const int TIMEOUT_MIC = 1000000;
const int TIMEOUT_PIR = 3000;
const int TIMEOUT_LCD = 10000;
// Other constants
const int RB_SIZE = 16;
const int DISPLAY_REFRESH_TIME = 1000;

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
// Temperatures:
// No person detected
int max_temp_fan = 30;
int min_temp_fan = 25;
int max_temp_heater = 20;
int min_temp_heater = 15;
// Person detected
int max_temp_fan_pers= 25;
int min_temp_fan_pers= 20;
int max_temp_heater_pers= 10;
int min_temp_heater_pers= 5;

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

void changeSetPoint(){
  
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
    lcd.print((int) (fanSpeed/255*100));
    lcd.print("% HT:");
    lcd.print((int)(heaterIntensity/255*100));
    lcd.print("%");
  }
  else{
    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("AC m:");
    lcd.print(local_pdp || local_mdp ? min_temp_fan_pers : min_temp_fan);
    lcd.print(" M:");
    lcd.print(local_pdp || local_mdp ? max_temp_fan_pers : max_temp_fan);
    lcd.setCursor(0,1);
    lcd.print("HT m:");
    lcd.print(local_pdp || local_mdp ? min_temp_heater_pers : min_temp_heater);
    lcd.print(" M:");
    lcd.print(local_pdp || local_mdp ?  max_temp_heater_pers : max_temp_heater);
    if(local_pdp||local_mdp){
      lcd.print(" pers");
    }
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

  //h
  Serial.begin(9600);
  while(!Serial){
    Serial.println("Doesnt print");
  }
  Serial.println("Serial will change the 4 current active set points (if people are in the room, will chage the pers values)");
  Serial.println("Format:");
  Serial.println("/10 14 09 13/");
  Serial.println("if no people detected: min_temp_fan =10, max_temp_fan=14, min_temp_heater=09, max_temp_heater=13");
  Serial.println("if people detected: min_temp_fan_pers =10, max_temp_fan_pers=14, min_temp_heater_pers=09, max_temp_heater_pers=13");
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
    fanSpeed = fanSpeedCalc(temp, (float) min_temp_fan_pers, (float) max_temp_fan_pers);
  } else {
    fanSpeed = fanSpeedCalc(temp, (float) max_temp_fan, (float) max_temp_fan);
  }
  analogWrite(FAN_PIN, fanSpeed);

  // b. 
  if(mic_detects_person || pir_detects_person){
    heaterIntensity = heaterIntensityCalc(temp, (float) min_temp_heater_pers , (float) max_temp_heater_pers);
  } else {
    heaterIntensity = heaterIntensityCalc(temp, (float) min_temp_heater , (float) max_temp_heater);
  }
  analogWrite(RLED_PIN, heaterIntensity);

  //c.
  noInterrupts();
  local_pdp = pir_detects_person;
  local_mdp = mic_detects_person;
  interrupts();

  // Lcd screen
  printLcd();
  delay(DISPLAY_REFRESH_TIME);
}

//Serial listener loop:
void loop2(){
  //h.
  yield();
  if(Serial.available()>0){
    char entranceByte=Serial.read();
    char charBytes[12];
    if(entranceByte=='/'){
      int i=0;
      while((entranceByte=Serial.read())!='/' && i<12){
        charBytes[i]=entranceByte;
        i++;
      }
      if(mic_detects_person || pir_detects_person){
        min_temp_fan_pers = ((int) charBytes[0]-INT_ASCII)*10+((int) charBytes[1]-INT_ASCII);
        max_temp_fan_pers = ((int) charBytes[3]-INT_ASCII)*10+((int) charBytes[4]-INT_ASCII);
        min_temp_heater_pers = ((int) charBytes[6]-INT_ASCII)*10+((int) charBytes[7]-INT_ASCII);
        max_temp_heater_pers = ((int) charBytes[9]-INT_ASCII)*10+((int) charBytes[10]-INT_ASCII);
      }
      else{
        min_temp_fan = ((int) charBytes[0]-INT_ASCII)*10+((int) charBytes[1]-INT_ASCII);
        max_temp_fan = ((int) charBytes[3]-INT_ASCII)*10+((int) charBytes[4]-INT_ASCII);
        min_temp_heater = ((int) charBytes[6]-INT_ASCII)*10+((int) charBytes[7]-INT_ASCII);
        max_temp_heater = ((int) charBytes[9]-INT_ASCII)*10+((int) charBytes[10]-INT_ASCII);
      } 
    }
  }
}