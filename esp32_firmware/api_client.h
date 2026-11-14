#pragma once
#include "sensors.h"
#include "esp_camera.h"
// Captured together by the control loop; copied atomically through a queue.
struct TelemetrySnapshot {
  SensorData sensors;
  const char* pumpState = "UNKNOWN";
  const char* growLightState = "UNKNOWN";
};
bool uploadPlantTelemetry(const TelemetrySnapshot& snapshot);
bool uploadPlantSnapshot(camera_fb_t* fb,const TelemetrySnapshot& snapshot);
