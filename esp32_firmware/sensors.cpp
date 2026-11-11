#include "sensors.h"
#include "config.h"
#include <Wire.h>
#include <DHT.h>
#include <BH1750.h>
#include <Adafruit_ADS1X15.h>
static DHT* dhtSensor = nullptr;
static BH1750 lightSensor;
static Adafruit_ADS1115 ads;
static bool lightReady = false, adsReady = false;

bool beginSensors() {
  if (PIN_DHT >= 0) { dhtSensor = new DHT(PIN_DHT, DHT_SENSOR_TYPE); dhtSensor->begin(); }
  else Serial.println("[SENSORS] DHT disabled: assign PIN_DHT");
  if (PIN_I2C_SDA >= 0 && PIN_I2C_SCL >= 0) {
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    lightReady = lightSensor.begin(BH1750::CONTINUOUS_HIGH_RES_MODE);
    adsReady = ads.begin();
    if (adsReady) ads.setGain(GAIN_ONE);
    Serial.printf("[SENSORS] BH1750=%s ADS1115=%s\n", lightReady ? "OK" : "FAIL", adsReady ? "OK" : "FAIL");
  } else Serial.println("[SENSORS] I2C disabled: assign SDA/SCL");
  return true;
}

SensorData readAllSensors() {
  SensorData d;
  if (dhtSensor) {
    float t = dhtSensor->readTemperature(), h = dhtSensor->readHumidity();
    if (!isnan(t) && !isnan(h)) { d.temperatureC=t; d.humidityPct=h; d.dhtValid=true; }
  }
  if (lightReady) { float lux=lightSensor.readLightLevel(); if (!isnan(lux) && lux >= 0) { d.lightLux=lux; d.lightValid=true; } }
  if (adsReady) {
    int16_t raw=ads.readADC_SingleEnded(SOIL_ADC_CHANNEL);
    float den=float(SOIL_ADC_DRY-SOIL_ADC_WET);
    if (den != 0) { d.soilMoisturePct=constrain(100.0f*(SOIL_ADC_DRY-raw)/den,0.0f,100.0f); d.soilValid=true; }
  }
  Serial.printf("[SENSORS] T=%.1fC RH=%.1f%% soil=%.1f%% lux=%.1f\n",d.temperatureC,d.humidityPct,d.soilMoisturePct,d.lightLux);
  return d;
}
