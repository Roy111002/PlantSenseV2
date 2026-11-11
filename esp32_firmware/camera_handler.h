#pragma once
#include "esp_camera.h"
bool beginCamera();
camera_fb_t* capturePlantImage();
void releasePlantImage(camera_fb_t* fb);
