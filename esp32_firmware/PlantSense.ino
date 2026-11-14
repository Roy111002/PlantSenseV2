#include <Arduino.h>
#include "config.h"
#include "sensors.h"
#include "automation.h"
#include "camera_handler.h"
#include "wifi_manager.h"
#include "api_client.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
static SensorData latest;
static QueueHandle_t snapshotQueue=nullptr;
static bool cameraReady=false;
static uint32_t lastSensor=0;

static void publishSnapshot(){
  TelemetrySnapshot snapshot;
  snapshot.sensors=latest;
  snapshot.pumpState=pumpReportedState();
  snapshot.growLightState=growLightReportedState();
  if(snapshotQueue)xQueueOverwrite(snapshotQueue,&snapshot);
}

static void telemetryTask(void*){
  uint32_t lastUpload=0;
  for(;;){
    maintainWiFi();
    uint32_t now=millis();
    if(now-lastUpload>=TELEMETRY_INTERVAL_MS){
      lastUpload=now;
      TelemetrySnapshot snapshot;
      if(wifiConnected() && xQueuePeek(snapshotQueue,&snapshot,0)==pdTRUE)
        uploadPlantTelemetry(snapshot);
    }
    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

static void imageTask(void*){
  for(;;){
    vTaskDelay(pdMS_TO_TICKS(IMAGE_INTERVAL_MS));
    TelemetrySnapshot snapshot;
    if(cameraReady && wifiConnected() && xQueuePeek(snapshotQueue,&snapshot,0)==pdTRUE){
      camera_fb_t* fb=capturePlantImage();
      if(fb){uploadPlantSnapshot(fb,snapshot);releasePlantImage(fb);}
    }
  }
}
void setup(){
  Serial.begin(115200);delay(800);Serial.println("\n=== PlantSense AI Pod ===");
  beginAutomation(); // outputs default OFF
  beginSensors();
  cameraReady=beginCamera();
  if(!cameraReady)Serial.println("[WARN] Camera unavailable; telemetry remains enabled");
  beginWiFi();
  latest=readAllSensors();lastSensor=millis();updateAutomation(latest);
  snapshotQueue=xQueueCreate(1,sizeof(TelemetrySnapshot));
  if(!snapshotQueue){Serial.println("[ERROR] Telemetry queue allocation failed");return;}
  publishSnapshot();
  if(xTaskCreate(telemetryTask,"telemetry",6144,nullptr,1,nullptr)!=pdPASS)
    Serial.println("[ERROR] Could not start telemetry task");
  if(cameraReady && xTaskCreate(imageTask,"plant-image",8192,nullptr,1,nullptr)!=pdPASS)
    Serial.println("[ERROR] Could not start image task");
}
void loop(){
  uint32_t now=millis();
  if(now-lastSensor>=SENSOR_INTERVAL_MS){lastSensor=now;latest=readAllSensors();}
  // Keep control deadlines independent of HTTP and AI latency.
  updateAutomation(latest);
  publishSnapshot();
  delay(20);
}
