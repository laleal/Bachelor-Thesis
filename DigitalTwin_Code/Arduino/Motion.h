#ifndef MOTION_H
#define MOTION_H

#include <Arduino.h>

class Motion {
public:
  Motion(uint8_t pin);
  void begin();
  bool isMotionDetected();

private:
  uint8_t _pin;
};

#endif
