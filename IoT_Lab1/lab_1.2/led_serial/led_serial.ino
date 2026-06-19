#include <MBED_RPi_Pico_TimerInterrupt.h>

const int RLED_PIN = 2; // costante per indicare il pin del red rosso
const int GLED_PIN = 3;// costante per indicare il pin del red verde

const long R_HALF_PERIOD = 1500l; //tempo in millisecondi
const long G_HALF_PERIOD = 350l; //tempo in millisecondi

volatile int redLedState = LOW; //iniziamo con LOW - STATE
volatile int greenLedState = LOW; //iniziamo con LOW - STATE
  
MBED_RPI_PICO_Timer ITimer1(1); // inizializza interrupt timer --> il timer numero 1 può generare un interrupt di tipo MBED_RPI_PICO_Timer

void blinkGreen(uint alarm_num){  // funzione di interupt
    TIMER_ISR_START(alarm_num); //inizio della procedura interrupt
    digitalWrite(GLED_PIN, greenLedState); // imposta lo stato per il led verde
    greenLedState = !greenLedState; //cambia lo stato per la prossima iterazione
    TIMER_ISR_END(alarm_num); //fine della procedura interrupt
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600); //inizializzazione della comunicazione seriale a 9600 baud
  while(!Serial) //finchè non serial
    Serial.println("Lab 1.2 Starting");

  pinMode(RLED_PIN, OUTPUT); //setta il pin fisico del led rosso
  pinMode(GLED_PIN, OUTPUT); //setta il pin fisico del led verde

  ITimer1.setInterval(G_HALF_PERIOD * 1000 , blinkGreen);
}

void loop() {
  // codice asincrono: blocca per il periodo di red
  if(Serial.available() > 0){ //finchè non riceviamo un input attendiamo
    int inByte = Serial.read(); //settiamo il carattere letto in inByte
    //di seguito il controllo se è rosso, verde o invalid
    if(inByte == 'r' || inByte == 'R' ){ // R da documentazione
      Serial.print("LED 2 status: ");
      Serial.println(redLedState);
    }
    else  if(inByte == 'l' || inByte == 'L'){ //L da documentazione
      Serial.print("LED 3 status: ");
      Serial.println(greenLedState);
    }
    else {
      Serial.println("Invalid command");
    }
  }

  digitalWrite(RLED_PIN, redLedState); // imposta lo stato per il led rosso
  redLedState = !redLedState; //cambia lo stato del red rosso
  delay(R_HALF_PERIOD); //aspetta un certo tempo R_HALF_PERIOD
}
