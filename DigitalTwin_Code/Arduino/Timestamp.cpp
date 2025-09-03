#include "Timestamp.h"
#include <time.h>

void initTimestamp() {

  configTime(0, 0, "pool.ntp.org"); //Sets up NTP

  time_t now = time(nullptr);
  unsigned long start = millis();

  while (now < 24 * 3600 && millis() - start < 5000) {
    delay(100);
    now = time(nullptr);
  }
}

//YYYY‑MM‑DDTHH:MM:SS.mmmZ or zeros
String getTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return String("0000-00-00T00:00:00.000Z");
  }

  uint16_t ms = (uint16_t)(millis() % 1000);

  char buf[32];
  sprintf(buf,
    "%04d-%02d-%02dT%02d:%02d:%02d.%03uZ",  // Z for UTC
    timeinfo.tm_year + 1900,
    timeinfo.tm_mon  + 1,
    timeinfo.tm_mday,
    timeinfo.tm_hour,
    timeinfo.tm_min,
    timeinfo.tm_sec,
    ms
  );
  return String(buf);
}