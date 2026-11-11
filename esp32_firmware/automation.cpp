#include "automation.h"
#include "config.h"
static bool pumpState=false, lightState=false;
static uint32_t pumpStartedAt=0, pumpLastStoppedAt=0;
static void output(int pin,bool on){ if(pin>=0) digitalWrite(pin,on?HIGH:LOW); }
void beginAutomation(){
  if(PIN_PUMP_MOSFET>=0){pinMode(PIN_PUMP_MOSFET,OUTPUT);output(PIN_PUMP_MOSFET,false);}
  if(PIN_LIGHT_MOSFET>=0){pinMode(PIN_LIGHT_MOSFET,OUTPUT);output(PIN_LIGHT_MOSFET,false);}
}
void updateAutomation(const SensorData& d){
  uint32_t now=millis();
  if(PIN_PUMP_MOSFET>=0 && d.soilValid){
    if(pumpState && now-pumpStartedAt>=MAX_PUMP_RUNTIME_MS){pumpState=false;pumpLastStoppedAt=now;output(PIN_PUMP_MOSFET,false);Serial.println("[CONTROL] Pump OFF: max runtime");}
    if(!pumpState && d.soilMoisturePct<SOIL_PUMP_ON_BELOW_PCT && (pumpLastStoppedAt==0 || now-pumpLastStoppedAt>=PUMP_COOLDOWN_MS)){pumpState=true;pumpStartedAt=now;output(PIN_PUMP_MOSFET,true);Serial.println("[CONTROL] Pump ON");}
    else if(pumpState && d.soilMoisturePct>=SOIL_PUMP_OFF_ABOVE_PCT){pumpState=false;pumpLastStoppedAt=now;output(PIN_PUMP_MOSFET,false);Serial.println("[CONTROL] Pump OFF: moisture recovered");}
  }
  if(PIN_LIGHT_MOSFET>=0 && d.lightValid){bool desired=d.lightLux<LIGHT_ON_BELOW_LUX;if(desired!=lightState){lightState=desired;output(PIN_LIGHT_MOSFET,lightState);Serial.printf("[CONTROL] Grow light %s\n",lightState?"ON":"OFF");}}
}
bool pumpIsOn(){return pumpState;}
bool growLightIsOn(){return lightState;}
