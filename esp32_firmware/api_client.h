#pragma once
#include "sensors.h"
#include "esp_camera.h"
bool uploadPlantSnapshot(camera_fb_t* fb,const SensorData& data);
