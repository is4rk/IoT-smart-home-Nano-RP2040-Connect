#include <Scheduler.h>

  const int RLED_PIN = 2; // costante per indicare il pin del red rosso
  const int GLED_PIN = 3;// costante per indicare il pin del red verde

  const long R_HALF_PERIOD = 1500l; //tempo in millisecondi
  const long G_HALF_PERIOD = 350l; //tempo in millisecondi

  int redLedState = LOW; //iniziamo con LOW - STATE
  int greenLedState = LOW; //iniziamo con LOW - STATE
  

void setup() {
  // put your setup code here, to run once:
  pinMode(RLED_PIN, OUTPUT); //setta il pin fisico del led rosso
  pinMode(GLED_PIN, OUTPUT); //setta il pin fisico del led verde
  Scheduler.startLoop(loop2); //inizializza un secondo loop
}

void loop() {
  // put your main code here, to run repeatedly:
  digitalWrite(RLED_PIN, redLedState); // imposta lo stato per il led rosso
  redLedState = !redLedState; //cambia lo stato del red rosso
  delay(R_HALF_PERIOD); //aspetta un certo tempo R_HALF_PERIOD
}

void loop2() {
  // put your main code here, to run repeatedly:
  digitalWrite(GLED_PIN, greenLedState); // imposta lo stato per il led verde
  greenLedState = !greenLedState; //cambia lo stato del red green
  delay(G_HALF_PERIOD); //aspetta un certo tempo G_HALF_PERIOD
}
