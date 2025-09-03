#ifndef TEMPERATURE_H
#define TEMPERATURE_H

#include <Wire.h>
#include "Adafruit_HTU21DF.h"

class Temperature {
public:
  Temperature();
  bool begin();
  float getTemperature();
  float getHumidity();

private:
  Adafruit_HTU21DF _htu;
};

#endif
