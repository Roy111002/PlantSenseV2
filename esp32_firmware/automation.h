#pragma once
#include "sensors.h"
void beginAutomation();
void updateAutomation(const SensorData& data);
bool pumpIsOn();
bool growLightIsOn();
const char* pumpReportedState();
const char* growLightReportedState();
