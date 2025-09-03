#ifndef CO2_H
#define CO2_H

#include <Arduino.h>
#include <MHZ19.h>
#include <HardwareSerial.h>

class Co2 {
public:
  Co2(HardwareSerial& serial, int rxPin, int txPin);
  
  void begin();
  float getPPM();

private:
  HardwareSerial& _serial;
  MHZ19           _mhz19;
  int             _rxPin;
  int             _txPin;
};

#endif
