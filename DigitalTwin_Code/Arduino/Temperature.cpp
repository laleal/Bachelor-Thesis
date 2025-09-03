#include "Temperature.h"

Temperature::Temperature() {
}

bool Temperature::begin() {
  return _htu.begin();
}

float Temperature::getTemperature() {
  return _htu.readTemperature(); 
}

float Temperature::getHumidity() {
  return _htu.readHumidity();
}
