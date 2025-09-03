#include "Co2.h"

Co2::Co2(HardwareSerial& serial, int rxPin, int txPin)
  : _serial(serial), _rxPin(rxPin), _txPin(txPin) {}

void Co2::begin() {
  _serial.begin(9600, SERIAL_8N1, _rxPin, _txPin);
  _mhz19.begin(_serial);
  _mhz19.autoCalibration(false);
}

float Co2::getPPM() {
  return _mhz19.getCO2();
}
