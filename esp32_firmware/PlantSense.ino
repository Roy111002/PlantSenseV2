#include <Arduino.h>
#include "config.h"
#include "sensors.h"
#include "automation.h"
#include "camera_handler.h"
#include "wifi_manager.h"
#include "api_client.h"
static SensorData latest;
static uint32_t lastSensor=0,lastImage=0;
void setup(){
  Serial.begin(115200);delay(800);Serial.println("\n=== PlantSense AI Pod ===");
  beginAutomation(); // outputs default OFF
  beginSensors();
  if(!beginCamera())Serial.println("[WARN] Camera unavailable; check board/camera/PSRAM");
  beginWiFi();
}
void loop(){
  uint32_t now=millis();maintainWiFi();
  if(now-lastSensor>=SENSOR_INTERVAL_MS){lastSensor=now;latest=readAllSensors();updateAutomation(latest);}
  if(now-lastImage>=IMAGE_INTERVAL_MS){lastImage=now;if(wifiConnected()){camera_fb_t* fb=capturePlantImage();if(fb){uploadPlantSnapshot(fb,latest);releasePlantImage(fb);}}else Serial.println("[AI] upload skipped: Wi-Fi offline");}
  delay(20);
}
