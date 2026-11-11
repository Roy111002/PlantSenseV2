#pragma once
#include <Arduino.h>
struct SensorData {
  float temperatureC = NAN, humidityPct = NAN, soilMoisturePct = NAN, lightLux = NAN;
  bool dhtValid = false, soilValid = false, lightValid = false;
};
bool beginSensors();
SensorData readAllSensors();
