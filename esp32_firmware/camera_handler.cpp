#include <Arduino.h>
#include "camera_handler.h"
#include "camera_pins.h"
#include "esp_timer.h"
bool beginCamera(){
  camera_config_t c = {};
  c.ledc_channel=LEDC_CHANNEL_0;c.ledc_timer=LEDC_TIMER_0;
  c.pin_d0=CAM_PIN_Y2;c.pin_d1=CAM_PIN_Y3;c.pin_d2=CAM_PIN_Y4;c.pin_d3=CAM_PIN_Y5;
  c.pin_d4=CAM_PIN_Y6;c.pin_d5=CAM_PIN_Y7;c.pin_d6=CAM_PIN_Y8;c.pin_d7=CAM_PIN_Y9;
  c.pin_xclk=CAM_PIN_XCLK;c.pin_pclk=CAM_PIN_PCLK;c.pin_vsync=CAM_PIN_VSYNC;c.pin_href=CAM_PIN_HREF;
  c.pin_sccb_sda=CAM_PIN_SIOD;c.pin_sccb_scl=CAM_PIN_SIOC;c.pin_pwdn=CAM_PIN_PWDN;c.pin_reset=CAM_PIN_RESET;
  c.xclk_freq_hz=20000000;c.pixel_format=PIXFORMAT_JPEG;
  // Start with a small JPEG and one buffer for periodic snapshots. Multiple
  // buffers enable continuous capture, which is unnecessary for this workflow.
  const bool hasPsram=psramFound();
  c.frame_size=FRAMESIZE_QVGA; // 320 x 240 for initial hardware validation
  c.jpeg_quality=20; // Higher number means more JPEG compression.
  c.fb_count=1;
  c.grab_mode=CAMERA_GRAB_WHEN_EMPTY;
  c.fb_location=hasPsram?CAMERA_FB_IN_PSRAM:CAMERA_FB_IN_DRAM;
  Serial.printf("[CAMERA] PSRAM=%s, JPEG=320x240, quality=20, buffers=1\n",hasPsram?"YES":"NO");
  esp_err_t e=esp_camera_init(&c);if(e!=ESP_OK){Serial.printf("[CAMERA] init failed 0x%x\n",e);return false;}
  sensor_t* sensor=esp_camera_sensor_get();
  if(sensor){
    Serial.printf("[CAMERA] sensor PID=0x%04x\n",sensor->id.PID);
    // Correct the user's upside-down mounting before storage and AI analysis.
    // Vertical flip + horizontal mirror together rotate the image 180 degrees.
    const int flipResult=sensor->set_vflip(sensor,1);
    const int mirrorResult=sensor->set_hmirror(sensor,1);
    if(flipResult==0 && mirrorResult==0)Serial.println("[CAMERA] rotation=180 degrees");
    else Serial.printf("[CAMERA] orientation setting failed: vflip=%d hmirror=%d\n",flipResult,mirrorResult);
  }
  Serial.println("[CAMERA] ready");return true;
}
camera_fb_t* capturePlantImage(){
  const int64_t requestedAt=esp_timer_get_time();
  // WHEN_EMPTY can retain a frame from the previous upload interval. Return
  // any pre-request frame and acquire again instead of sending an old scene.
  for(int attempt=0;attempt<4;++attempt){
    camera_fb_t* fb=esp_camera_fb_get();
    if(!fb){Serial.println("[CAMERA] capture failed");return nullptr;}
    const int64_t capturedAt=(int64_t)fb->timestamp.tv_sec*1000000LL+fb->timestamp.tv_usec;
    const int64_t age=esp_timer_get_time()-capturedAt;
    if(capturedAt>=requestedAt && age>=0 && age<=2000000){
      Serial.printf("[CAMERA] fresh frame: %u bytes, age=%lu ms\n",(unsigned)fb->len,(unsigned long)(age/1000));
      return fb;
    }
    Serial.println("[CAMERA] discarded buffered/stale frame");
    esp_camera_fb_return(fb);
  }
  Serial.println("[CAMERA] no fresh frame available; skipped upload");return nullptr;
}
void releasePlantImage(camera_fb_t* fb){if(fb)esp_camera_fb_return(fb);}
