#include "Light.h"

Light::Light(uint8_t address)
  : _address(address) {
}

bool Light::begin() {
  if (!_sensor.begin(BH1750::ONE_TIME_HIGH_RES_MODE, _address, &Wire)) {
    return false;
  }
  return true;
}

void Light::wakeUp() {
  Wire.beginTransmission(_address);
  Wire.write(0x01); // Power ON
  Wire.endTransmission();
  delay(10);
}

float Light::getLux() {
  // sometimes the sensor does not wake up by itself.
  wakeUp();
  _sensor.begin(BH1750::ONE_TIME_HIGH_RES_MODE, _address, &Wire);
  delay(200);
  
  return _sensor.readLightLevel();
}
