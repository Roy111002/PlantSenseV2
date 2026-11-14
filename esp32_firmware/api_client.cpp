#include "api_client.h"
#include "config.h"
#include "automation.h"
#include "wifi_manager.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "esp_heap_caps.h"

bool uploadPlantTelemetry(const TelemetrySnapshot& snapshot){
  if(!wifiConnected())return false;
  const SensorData& d=snapshot.sensors;
  StaticJsonDocument<768> doc;
  doc["device_id"]=DEVICE_ID;doc["plant_species"]=PLANT_SPECIES;
  if(d.dhtValid){doc["temperature_c"]=d.temperatureC;doc["humidity_pct"]=d.humidityPct;}
  if(d.soilValid)doc["soil_moisture_pct"]=d.soilMoisturePct;
  if(d.lightValid)doc["light_lux"]=d.lightLux;
  doc["pump_state"]=snapshot.pumpState;doc["grow_light_state"]=snapshot.growLightState;
  String payload;serializeJson(doc,payload);
  HTTPClient http;http.setConnectTimeout(3000);http.setTimeout(4000);
  if(!http.begin(API_TELEMETRY_URL))return false;
  http.addHeader("Content-Type","application/json");
  if(DEVICE_API_TOKEN[0])http.addHeader("X-Device-Token",DEVICE_API_TOKEN);
  int code=http.POST(payload);
  Serial.printf("[TELEMETRY] HTTP %d\n",code);
  http.end();return code>=200&&code<300;
}

bool uploadPlantSnapshot(camera_fb_t* fb,const TelemetrySnapshot& snapshot){
  const SensorData& d=snapshot.sensors;
  if(!fb || !wifiConnected())return false;
  const String boundary="----PlantSenseBoundary7MA4YWxk";String head;
  auto field=[&](const char* n,const String& v){head+="--"+boundary+"\r\nContent-Disposition: form-data; name=\""+String(n)+"\"\r\n\r\n"+v+"\r\n";};
  field("device_id",DEVICE_ID);field("plant_species",PLANT_SPECIES);field("growth_stage",GROWTH_STAGE);
  field("temperature_c",d.dhtValid?String(d.temperatureC,2):"");field("humidity_pct",d.dhtValid?String(d.humidityPct,2):"");
  field("soil_moisture_pct",d.soilValid?String(d.soilMoisturePct,2):"");field("light_lux",d.lightValid?String(d.lightLux,1):"");
  field("pump_state",snapshot.pumpState);field("grow_light_state",snapshot.growLightState);
  head+="--"+boundary+"\r\nContent-Disposition: form-data; name=\"image\"; filename=\"plant.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n";
  String tail="\r\n--"+boundary+"--\r\n";size_t total=head.length()+fb->len+tail.length();
  uint8_t* payload=(uint8_t*)heap_caps_malloc(total,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);if(!payload)payload=(uint8_t*)malloc(total);if(!payload){Serial.println("[API] allocation failed");return false;}
  size_t off=0;memcpy(payload+off,head.c_str(),head.length());off+=head.length();memcpy(payload+off,fb->buf,fb->len);off+=fb->len;memcpy(payload+off,tail.c_str(),tail.length());
  HTTPClient http;http.setTimeout(HTTP_TIMEOUT_MS);if(!http.begin(API_ANALYZE_URL)){free(payload);return false;}
  http.addHeader("Content-Type","multipart/form-data; boundary="+boundary);
  if(DEVICE_API_TOKEN[0])http.addHeader("X-Device-Token",DEVICE_API_TOKEN);
  int code=http.POST(payload,total);free(payload);
  if(code>0){String response=http.getString();Serial.printf("[API] HTTP %d\n%s\n",code,response.c_str());}
  else Serial.printf("[API] error %s\n",http.errorToString(code).c_str());
  http.end();return code>=200&&code<300;
}
