#include "Motion.h"

Motion::Motion(uint8_t pin)
  : _pin(pin) {
}

void Motion::begin() {
  pinMode(_pin, INPUT);
}

bool Motion::isMotionDetected() {
  return (digitalRead(_pin) == HIGH);
}
