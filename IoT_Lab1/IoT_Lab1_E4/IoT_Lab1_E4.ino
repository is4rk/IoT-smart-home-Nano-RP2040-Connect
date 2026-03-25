  int current_speed = 0; // usiamo int perchè scegliamo un passo divisore di 255 (17) --> 15 passi
  const int FAN_PIN = 16; // avendo un range di velocità è un analog

void setup() {
  // put your setup code here, to run once:
  pinMode(FAN_PIN, OUTPUT);
  analogWrite(FAN_PIN, current_speed);
}

void loop() {
  // put your main code here, to run repeatedly:
  if(Serial.available()>0){
    int inByte = Serial.read();
    if( inByte == '+' ){
      if (current_speed <255){
        //aumento
        current_speed += 17;
        Serial.print("Increasing speed: ");
        Serial.println(current_speed);
      }
      else{
        Serial.println("Already at max speed");
      }
    }
    else if (inByte == '-' ){
      if (current_speed > 0 ){
        //decrementa
        current_speed -= 17;
        Serial.print("Decreasing speed: ");
        Serial.println(current_speed);
      }
      else{
        Serial.println("Already at min speed");
      }
    }
    else{
      Serial.println("Invalid command");
    }
  }
  analogWrite(FAN_PIN, current_speed);
}
