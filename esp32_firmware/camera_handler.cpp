#include "camera_handler.h"
#include "camera_pins.h"
bool beginCamera(){
  camera_config_t c;
  c.ledc_channel=LEDC_CHANNEL_0;c.ledc_timer=LEDC_TIMER_0;
  c.pin_d0=CAM_PIN_Y2;c.pin_d1=CAM_PIN_Y3;c.pin_d2=CAM_PIN_Y4;c.pin_d3=CAM_PIN_Y5;
  c.pin_d4=CAM_PIN_Y6;c.pin_d5=CAM_PIN_Y7;c.pin_d6=CAM_PIN_Y8;c.pin_d7=CAM_PIN_Y9;
  c.pin_xclk=CAM_PIN_XCLK;c.pin_pclk=CAM_PIN_PCLK;c.pin_vsync=CAM_PIN_VSYNC;c.pin_href=CAM_PIN_HREF;
  c.pin_sccb_sda=CAM_PIN_SIOD;c.pin_sccb_scl=CAM_PIN_SIOC;c.pin_pwdn=CAM_PIN_PWDN;c.pin_reset=CAM_PIN_RESET;
  c.xclk_freq_hz=20000000;c.pixel_format=PIXFORMAT_JPEG;
  if(psramFound()){c.frame_size=FRAMESIZE_VGA;c.jpeg_quality=12;c.fb_count=2;c.grab_mode=CAMERA_GRAB_LATEST;c.fb_location=CAMERA_FB_IN_PSRAM;}
  else{c.frame_size=FRAMESIZE_QVGA;c.jpeg_quality=14;c.fb_count=1;c.grab_mode=CAMERA_GRAB_WHEN_EMPTY;c.fb_location=CAMERA_FB_IN_DRAM;}
  esp_err_t e=esp_camera_init(&c);if(e!=ESP_OK){Serial.printf("[CAMERA] init failed 0x%x\n",e);return false;}Serial.println("[CAMERA] ready");return true;
}
camera_fb_t* capturePlantImage(){camera_fb_t* fb=esp_camera_fb_get();if(!fb)Serial.println("[CAMERA] capture failed");else Serial.printf("[CAMERA] %u bytes\n",(unsigned)fb->len);return fb;}
void releasePlantImage(camera_fb_t* fb){if(fb)esp_camera_fb_return(fb);}
