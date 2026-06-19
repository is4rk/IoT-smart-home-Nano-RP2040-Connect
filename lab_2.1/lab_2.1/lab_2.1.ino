// includes
#include <LiquidCrystal_PCF8574.h>
#include <MBED_RPi_Pico_TimerInterrupt.h> 
#include <PDM.h>
#include <Scheduler.h>

  /*************/
 /* CONSTANTS */
/*************/
// How much to remove from char to get int. ASCII(0) = decimal 49
const int INT_ASCII = 48;
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
const int TIMEOUT_MIC = 40000;
const int TIMEOUT_PIR = 30000;
const int TIMEOUT_LCD = 10000; // Timeout to change the page shown on the display
// Sound constants
const int MAX_THRESHOLD = 800;
const int N_SOUND_EVENTS = 800;
const int SOUND_INTERVAL = 1000;
// Other constants
const int RB_SIZE = 16;
const int DISPLAY_REFRESH_TIME = 1000; // Delay to update infos shown on display

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
MBED_RPI_PICO_Timer ITimer2(2);
MBED_RPI_PICO_Timer ITimer3(3);

  /*************/
 /* FUNCTIONS */
/*************/

// Microphone data ISR handler
void onPDMdata(){
  // Check how many samples arrived
  int bytesAvailable = PDM.available();
  PDM.read(sampleBuffer, bytesAvailable);
  samplesRead = bytesAvailable / 2;

  if(samplesRead){
    for(int i = 0; i < samplesRead; i++){
      // Register time of events with a significant value
      if(abs(sampleBuffer[i]) > MAX_THRESHOLD) {  //measured with fan on max speed 
        ringBuffer[indexRB % RB_SIZE] = millis();
        indexRB++;
        
        // If there are at least 10 data in the ring buffer and the 10 events happened in less then SOUND_INTERVAL, presence is detected
        if(indexRB >= (N_SOUND_EVENTS - 1) && (ringBuffer[(indexRB-1) % RB_SIZE]- ringBuffer[(indexRB-N_SOUND_EVENTS) % RB_SIZE]) < SOUND_INTERVAL){
          mic_detects_person = 1;
          resetMicrophoneTimer();
        }
      }
    samplesRead = 0;
    }
  }
}

// Interrupt timers to reset people presence in the room, for the pir and the mic
void timerDonePir(uint alarm_num){
  TIMER_ISR_START(alarm_num);
  // If timer ends, no person in the room
  pir_detects_person = 0;
  TIMER_ISR_END(alarm_num);
}

void timerDoneMic(uint alarm_num){
  TIMER_ISR_START(alarm_num);
  // If timer ends, no person in the room
  mic_detects_person = 0;
  TIMER_ISR_END(alarm_num);
}

// Set pir presence to true and reset timer to reset the person detection from the pir
void foundPresencePir(){
  pir_detects_person=1;
  ITimer1.setInterval(TIMEOUT_PIR * 1000 , timerDonePir); 
}

// Reset person detection from the mic
void resetMicrophoneTimer(){
  ITimer2.setInterval(TIMEOUT_MIC * 1000 , timerDoneMic); 
}

// Functions to calculate fan speed and heater intensity proportionally to the set values passed
int heaterIntensityCalc(float temp, float tmin, float tmax){
  if(temp <= tmin) return 255;
  if(temp >= tmax) return 0; 
  return (int) (255.0 * (1.0 - ((temp - tmin) / (tmax - tmin))));
}

int fanSpeedCalc(float temp, float tmin, float tmax){
  if (temp <= tmin) return 0;
  if (temp >= tmax) return 255; 
  return (int) (255.0 * (temp - tmin) / (tmax - tmin));
}

// Classic analog to °C temp converter
float tempConverter(int a){
  float R = ((VCC/(float) a) - 1)*R0;
  float T = 1/((log( (float) R/ (float) R0)/ (float) B) + (1/298.15));
  T = T - 273.15;
  return T;
}

// Interrupt timer to change the display shown on the lcd screen
void lcdChangeState(uint alarm_num){
  TIMER_ISR_START(alarm_num);
  lcd_state =  !lcd_state;
  TIMER_ISR_END(alarm_num);
}

// Display print function
void printLcd(){
  //g.
  if(lcd_state){
    lcd.clear();
    lcd.setCursor(0,0);
    lcd.print("T:");
    lcd.print(temp);
    lcd.print(" Pres:");
    lcd.print((int)(local_pdp||local_mdp));
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
  }
}

// Initialization print
void printStart(){
  Serial.println("  _____                      __ ");
  Serial.println(" / ____|                    /_ |");
  Serial.println("| |  __ _ __ ___  _   _ _ __ | |");
  Serial.println("| | |_ | '__/ _ \\| | | | '_ \\| |");
  Serial.println("| |__| | | | (_) | |_| | |_) | |");
  Serial.println(" \\_____|_|  \\___/ \\__,_| .__/|_|");
  Serial.println("                       | |      ");
  Serial.println("                       |_|      ");
  delay(100);
  Serial.println("Serial will change the 4 current active set points (if people are in the room, will chage the pers values)");
  delay(100);
  Serial.println("Format: \"/xx xx xx xx/\" where x = digit");
  Serial.println("/minAC maxAC minHT maxHT/");
  delay(100);
  Serial.println("Example:");
  Serial.println("/10 14 09 13/");
  Serial.println("if no people detected: min_temp_fan =10, max_temp_fan=14, min_temp_heater=09, max_temp_heater=13");
  Serial.println("if people detected: min_temp_fan_pers =10, max_temp_fan_pers=14, min_temp_heater_pers=09, max_temp_heater_pers=13");
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
  while (!Serial);
  Serial.println("Starting...");
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

  printStart();
}


  /*********/
 /* LOOPS */
/*********/
// Main loop:
void loop() {
  //c.
  noInterrupts();
  // Update presence without interupt conflicts
  local_pdp = pir_detects_person;
  local_mdp = mic_detects_person;
  interrupts();

  // a.
  int x = analogRead(TEMP_PIN);
  temp = tempConverter(x);
  
  // Change set point values if we detect people in the room
  if(local_mdp || local_pdp){
    fanSpeed = fanSpeedCalc(temp, (float) min_temp_fan_pers, (float) max_temp_fan_pers);
  } else {
    fanSpeed = fanSpeedCalc(temp, (float) min_temp_fan, (float) max_temp_fan);
  }
  analogWrite(FAN_PIN, fanSpeed);

  // b. 
  // Change set point values if we detect people in the room
  if(local_mdp || local_pdp){
    heaterIntensity = heaterIntensityCalc(temp, (float) min_temp_heater_pers , (float) max_temp_heater_pers);
  } else {
    heaterIntensity = heaterIntensityCalc(temp, (float) min_temp_heater , (float) max_temp_heater);
  }
  analogWrite(RLED_PIN, heaterIntensity);

  // Lcd screen
  printLcd();
  delay(DISPLAY_REFRESH_TIME);
}

//Serial listener loop:
void loop2(){
  //h.
  if(Serial.available()>0){
    // Format: "/xx xx xx xx/" where x = digit
    char entranceByte=Serial.read();
    char charBytes[12];

    if(entranceByte=='/'){
      int i=0;
      while((entranceByte=Serial.read())!='/' && i<12){
        charBytes[i]=entranceByte;
        i++;
      }

      // Change set point values
      if(local_mdp || local_pdp){
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
  yield();
}