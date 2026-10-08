#include <config.h>

void setup() {
  // put your setup code here, to run once:
  DEBUG_SERIAL.begin(DEBUG_BAUDRATE);
  DEBUG_SERIAL.println("Setup started");
}

void loop() {
  // put your main code here, to run repeatedly:
  DEBUG_SERIAL.println("Loop started");
  delay(1000);
}
