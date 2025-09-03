#ifndef LIGHT_H
#define LIGHT_H

#include <Wire.h>
#include <BH1750.h>

class Light {
public:
  Light(uint8_t address = 0x23);
  bool begin();
  float getLux();

private:
  uint8_t _address;
  BH1750 _sensor;
  void wakeUp();
};

#endif
