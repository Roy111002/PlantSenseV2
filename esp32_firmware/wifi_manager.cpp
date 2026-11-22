#include "wifi_manager.h"
#include "config.h"
#include <WiFi.h>
static uint32_t lastAttempt=0;
static bool reportedConnected=false;
void beginWiFi(){
  WiFi.mode(WIFI_STA);
  // Controlled latency test: keep the radio awake while the USB-powered pod runs.
  // This does not repair a wrong server address or a broken network path.
  const bool sleepDisabled=WiFi.setSleep(false);
  Serial.printf("[WIFI] modem sleep disable=%s\n",sleepDisabled?"OK":"FAILED");
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID,WIFI_PASSWORD);
  lastAttempt=millis();
  Serial.println("[WIFI] connecting");
}
void maintainWiFi(){
  if(WiFi.status()==WL_CONNECTED){
    if(!reportedConnected){
      Serial.printf("[WIFI] connected: ip=%s gateway=%s RSSI=%d dBm\n",WiFi.localIP().toString().c_str(),WiFi.gatewayIP().toString().c_str(),WiFi.RSSI());
      reportedConnected=true;
    }
    return;
  }
  if(reportedConnected){Serial.printf("[WIFI] connection lost: status=%d\n",(int)WiFi.status());reportedConnected=false;}
  if(millis()-lastAttempt<WIFI_RETRY_INTERVAL_MS)return;
  lastAttempt=millis();
  Serial.printf("[WIFI] reconnecting: status=%d\n",(int)WiFi.status());
  WiFi.reconnect();
}
bool wifiConnected(){return WiFi.status()==WL_CONNECTED;}
