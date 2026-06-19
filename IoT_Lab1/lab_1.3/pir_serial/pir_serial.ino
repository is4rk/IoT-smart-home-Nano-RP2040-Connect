  const int LED_PIN = 2; // costante per indicare il pin del red rosso
  const int PIR_PIN = 12 ; // costante per indicare il pin del PIR
  volatile int tot_count = 0; //volatile serve a dire al compilatore che il valore della variabile può cambiare in modo non prevedibile dal normale flusso di esecuzione, per esempio a causa di una ISR. Di conseguenza il compilatore deve evitare ottimizzazioni aggressive, come tenere il valore in registro e riusarlo senza rileggerlo dalla memoria.
  int ledState = LOW; //iniziamo con LOW - STATE
  int a=0;

void checkPresence(){
  ledState = !ledState;
  if(!ledState){
    tot_count++;
  }
  digitalWrite(LED_PIN, ledState);
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600); //inizializzazione della comunicazione seriale a 9600 baud
  while(!Serial) //finchè non serial
    Serial.println("Lab 1.3 Starting");
  pinMode(LED_PIN, OUTPUT);
  pinMode(PIR_PIN, INPUT); 
  attachInterrupt(digitalPinToInterrupt(PIR_PIN), checkPresence, CHANGE); //chiama interrupt checkPresence sul cambio di tensione del PIR_PIN
}

void loop() {
  // put your main code here, to run repeatedly:
  delay(3000);
  noInterrupts();
  a = tot_count;
  interrupts();
  Serial.print("Total people count: ");
  Serial.println(a);
}
