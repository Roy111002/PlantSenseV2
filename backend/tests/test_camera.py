"""Exercise actual capture code against stale/fresh camera driver frames."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(shutil.which("g++"),"g++ is required for the camera simulation")
class CameraTests(unittest.TestCase):
    def test_stale_frames_discarded_and_rotation_preserved(self):
        firmware=Path(__file__).resolve().parents[2]/"esp32_firmware"
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ("camera_handler.cpp","camera_handler.h","camera_pins.h"):
                shutil.copyfile(firmware/name,root/name)
            (root/"Arduino.h").write_text('''#pragma once
#include <cstdint>
inline bool psramFound(){return true;}
struct SerialStub { void println(const char*){} template<class... T> void printf(const char*,T...){} };
extern SerialStub Serial;
''')
            (root/"esp_timer.h").write_text('''#pragma once
#include <cstdint>
extern int64_t clockUs;
inline int64_t esp_timer_get_time(){return clockUs;}
''')
            (root/"esp_camera.h").write_text('''#pragma once
#include <cstdint>
#include <cstddef>
using esp_err_t=int;
constexpr int ESP_OK=0,LEDC_CHANNEL_0=0,LEDC_TIMER_0=0,PIXFORMAT_JPEG=1,FRAMESIZE_QVGA=2;
constexpr int CAMERA_GRAB_WHEN_EMPTY=1,CAMERA_FB_IN_PSRAM=1,CAMERA_FB_IN_DRAM=2;
struct camera_config_t {
 int ledc_channel,ledc_timer,pin_d0,pin_d1,pin_d2,pin_d3,pin_d4,pin_d5,pin_d6,pin_d7;
 int pin_xclk,pin_pclk,pin_vsync,pin_href,pin_sccb_sda,pin_sccb_scl,pin_pwdn,pin_reset;
 int xclk_freq_hz,pixel_format,frame_size,jpeg_quality,fb_count,grab_mode,fb_location;
};
struct camera_fb_t {size_t len;struct {long tv_sec,tv_usec;} timestamp;};
struct sensor_t {struct {int PID;} id;int (*set_vflip)(sensor_t*,int);int (*set_hmirror)(sensor_t*,int);};
esp_err_t esp_camera_init(camera_config_t*);
sensor_t* esp_camera_sensor_get();
camera_fb_t* esp_camera_fb_get();
void esp_camera_fb_return(camera_fb_t*);
''')
            (root/"main.cpp").write_text('''#include "Arduino.h"
#include "camera_handler.h"
#include <cassert>
SerialStub Serial;int64_t clockUs=10000000;int calls=0,returned=0,mode=0,flip=0,mirror=0;
camera_fb_t stale={100,{1,0}},fresh={200,{11,0}};
int setFlip(sensor_t*,int value){flip=value;return 0;}
int setMirror(sensor_t*,int value){mirror=value;return 0;}
sensor_t sensor={{0x3660},setFlip,setMirror};
esp_err_t esp_camera_init(camera_config_t* c){
 assert(c->frame_size==FRAMESIZE_QVGA && c->fb_count==1);
 assert(c->grab_mode==CAMERA_GRAB_WHEN_EMPTY);return ESP_OK;
}
sensor_t* esp_camera_sensor_get(){return &sensor;}
camera_fb_t* esp_camera_fb_get(){
 ++calls;
 if(mode==1)return &stale;
 if(mode==2)return nullptr;
 if(calls==1)return &stale;
 clockUs=11100000;return &fresh;
}
void esp_camera_fb_return(camera_fb_t*){++returned;}
int main(){
 assert(beginCamera());assert(flip==1 && mirror==1);
 assert(capturePlantImage()==&fresh);assert(returned==1);
 mode=1;calls=0;returned=0;
 assert(capturePlantImage()==nullptr);assert(calls==4 && returned==4);
 mode=2;calls=0;returned=0;
 assert(capturePlantImage()==nullptr);assert(calls==1 && returned==0);
}
''')
            binary=root/"camera-test.exe"
            subprocess.run([shutil.which("g++"),"-std=c++11","-I",str(root),
                            str(root/"camera_handler.cpp"),str(root/"main.cpp"),"-o",str(binary)],
                           check=True,capture_output=True,text=True)
            subprocess.run([str(binary)],check=True,capture_output=True,text=True)
