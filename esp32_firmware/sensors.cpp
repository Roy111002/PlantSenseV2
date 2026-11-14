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
static bool soilAdcPresent(){
  Wire.beginTransmission(SOIL_ADC_I2C_ADDRESS);
  return Wire.endTransmission()==0;
}

bool beginSensors() {
  if (PIN_DHT >= 0) { dhtSensor = new DHT(PIN_DHT, DHT_SENSOR_TYPE); dhtSensor->begin(); }
  else Serial.println("[SENSORS] DHT disabled: assign PIN_DHT");
  if (PIN_I2C_SDA >= 0 && PIN_I2C_SCL >= 0) {
    Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
    Wire.setTimeOut(20);
    lightReady = lightSensor.begin(BH1750::CONTINUOUS_HIGH_RES_MODE,LIGHT_I2C_ADDRESS,&Wire);
    adsReady = ads.begin(SOIL_ADC_I2C_ADDRESS,&Wire);
    if (adsReady) ads.setGain(GAIN_ONE);
    Serial.printf("[SENSORS] BH1750=%s ADS1115=%s\n", lightReady ? "OK" : "FAIL", adsReady ? "OK" : "FAIL");
  } else Serial.println("[SENSORS] I2C disabled: assign SDA/SCL");
  return true;
}

SensorData readAllSensors() {
  SensorData d;
  if (dhtSensor) {
    float t = dhtSensor->readTemperature(), h = dhtSensor->readHumidity();
    if (isfinite(t) && isfinite(h) && t>=-20 && t<=80 && h>=0 && h<=100) { d.temperatureC=t; d.humidityPct=h; d.dhtValid=true; }
  }
  if (lightReady) { float lux=lightSensor.readLightLevel(); if (isfinite(lux) && lux >= 0) { d.lightLux=lux; d.lightValid=true; } }
  if (adsReady && SOIL_ADC_CHANNEL<=3 && soilAdcPresent()) {
    const uint16_t mux[]={ADS1X15_REG_CONFIG_MUX_SINGLE_0,ADS1X15_REG_CONFIG_MUX_SINGLE_1,ADS1X15_REG_CONFIG_MUX_SINGLE_2,ADS1X15_REG_CONFIG_MUX_SINGLE_3};
    ads.startADCReading(mux[SOIL_ADC_CHANNEL],false);
    uint32_t started=millis();
    bool complete=false;
    do {complete=ads.conversionComplete();if(!complete)delay(1);} while(!complete && millis()-started<40);
    float den=float(SOIL_ADC_DRY-SOIL_ADC_WET);
    if (complete && den != 0 && soilAdcPresent()) {
      int16_t raw=ads.getLastConversionResults();
      Serial.printf("[SOIL] ADS1115 A%u raw=%d (dry=%d wet=%d; calibration required)\n",SOIL_ADC_CHANNEL,raw,SOIL_ADC_DRY,SOIL_ADC_WET);
      if(soilAdcPresent()){d.soilMoisturePct=constrain(100.0f*(SOIL_ADC_DRY-raw)/den,0.0f,100.0f);d.soilValid=true;}
    }
  }
  Serial.printf("[SENSORS] T=%.1fC RH=%.1f%% soil=%.1f%% lux=%.1f\n",d.temperatureC,d.humidityPct,d.soilMoisturePct,d.lightLux);
  return d;
}
