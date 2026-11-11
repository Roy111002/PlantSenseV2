#include "wifi_manager.h"
#include "config.h"
#include <WiFi.h>
static uint32_t lastAttempt=0;
void beginWiFi(){WiFi.mode(WIFI_STA);WiFi.begin(WIFI_SSID,WIFI_PASSWORD);lastAttempt=millis();Serial.println("[WIFI] connecting");}
void maintainWiFi(){if(WiFi.status()==WL_CONNECTED)return;if(millis()-lastAttempt<WIFI_RETRY_INTERVAL_MS)return;lastAttempt=millis();WiFi.disconnect();WiFi.begin(WIFI_SSID,WIFI_PASSWORD);Serial.println("[WIFI] reconnecting");}
bool wifiConnected(){return WiFi.status()==WL_CONNECTED;}
