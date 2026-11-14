"""Run real automation.cpp against simulated GPIOs and a deterministic clock."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("g++"), "g++ is required for the GPIO simulation")
class AutomationTests(unittest.TestCase):
    def test_gpio_reporting_deadline_sensor_failure_and_cooldown(self):
        firmware = Path(__file__).resolve().parents[2] / "esp32_firmware"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("automation.cpp", "automation.h", "sensors.h"):
                shutil.copyfile(firmware / name, root / name)
            (root / "Arduino.h").write_text('''#pragma once
#include <cmath>
#include <cstdint>
#define HIGH 1
#define LOW 0
#define OUTPUT 1
extern uint32_t clockMs;
extern int levels[16];
inline uint32_t millis(){return clockMs;}
inline void pinMode(int,int){}
inline void digitalWrite(int pin,int value){levels[pin]=value;}
inline int digitalRead(int pin){return levels[pin];}
struct SerialStub { void println(const char*){} template<class... T> void printf(const char*,T...){} };
extern SerialStub Serial;
''')
            (root / "config.h").write_text('''#pragma once
#include "Arduino.h"
#ifdef DISABLED_PINS
constexpr int PIN_PUMP_MOSFET=-1, PIN_LIGHT_MOSFET=-1;
#else
constexpr int PIN_PUMP_MOSFET=1, PIN_LIGHT_MOSFET=2;
#endif
constexpr float SOIL_PUMP_ON_BELOW_PCT=30, SOIL_PUMP_OFF_ABOVE_PCT=42, LIGHT_ON_BELOW_LUX=2000;
constexpr uint32_t MAX_PUMP_RUNTIME_MS=8000, PUMP_COOLDOWN_MS=60000;
''')
            (root / "main.cpp").write_text('''#include "automation.h"
#include <cassert>
#include <cstring>
uint32_t clockMs=0; int levels[16]={}; SerialStub Serial;
int main(){
 beginAutomation();
#ifdef DISABLED_PINS
 assert(std::strcmp(pumpReportedState(),"UNKNOWN")==0);
 assert(std::strcmp(growLightReportedState(),"UNKNOWN")==0);
#else
 assert(std::strcmp(pumpReportedState(),"OFF")==0);
 SensorData d;d.soilValid=true;d.soilMoisturePct=20;d.lightValid=true;d.lightLux=0;
 updateAutomation(d);
 assert(pumpIsOn() && growLightIsOn());
 assert(std::strcmp(pumpReportedState(),"ON")==0);
 assert(std::strcmp(growLightReportedState(),"ON")==0);
 clockMs=7999;updateAutomation(d);assert(pumpIsOn());
 clockMs=8000;updateAutomation(d);assert(!pumpIsOn());
 clockMs=67999;updateAutomation(d);assert(!pumpIsOn());
 clockMs=68000;updateAutomation(d);assert(pumpIsOn());
 d.soilValid=false;d.lightValid=false;updateAutomation(d);
 assert(!pumpIsOn() && !growLightIsOn());
 assert(std::strcmp(pumpReportedState(),"OFF")==0);
 d.soilValid=true;clockMs=128000;updateAutomation(d);assert(pumpIsOn());
 d.soilMoisturePct=42;updateAutomation(d);assert(!pumpIsOn());
#endif
}
''')
            for disabled in (False, True):
                with self.subTest(disabled_pins=disabled):
                    binary = root / ("disabled.exe" if disabled else "configured.exe")
                    command = [shutil.which("g++"), "-std=c++11", "-I", str(root),
                               str(root / "automation.cpp"), str(root / "main.cpp"),
                               "-o", str(binary)]
                    if disabled:
                        command.append("-DDISABLED_PINS")
                    subprocess.run(command, check=True, capture_output=True, text=True)
                    subprocess.run([str(binary)], check=True, capture_output=True, text=True)


if __name__ == "__main__":
    unittest.main()
