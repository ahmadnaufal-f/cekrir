#include <Arduino.h>
#include <esp_camera.h>

#include "camera_pins.h"

namespace {
constexpr uint32_t kCheckIntervalMs = 3000;
uint32_t lastCheck = 0;
bool cameraReady = false;

bool startCamera() {
  if (!psramFound()) {
    Serial.println("ERROR: PSRAM not detected. Check the board profile and power.");
    return false;
  }

  camera_config_t camera = {};
  camera.ledc_channel = LEDC_CHANNEL_0;
  camera.ledc_timer = LEDC_TIMER_0;
  camera.pin_d0 = camera_pins::kD0;
  camera.pin_d1 = camera_pins::kD1;
  camera.pin_d2 = camera_pins::kD2;
  camera.pin_d3 = camera_pins::kD3;
  camera.pin_d4 = camera_pins::kD4;
  camera.pin_d5 = camera_pins::kD5;
  camera.pin_d6 = camera_pins::kD6;
  camera.pin_d7 = camera_pins::kD7;
  camera.pin_xclk = camera_pins::kXclk;
  camera.pin_pclk = camera_pins::kPclk;
  camera.pin_vsync = camera_pins::kVsync;
  camera.pin_href = camera_pins::kHref;
  camera.pin_sccb_sda = camera_pins::kSda;
  camera.pin_sccb_scl = camera_pins::kScl;
  camera.pin_pwdn = camera_pins::kPwdn;
  camera.pin_reset = camera_pins::kReset;
  camera.xclk_freq_hz = 20000000;
  camera.pixel_format = PIXFORMAT_JPEG;
  camera.frame_size = FRAMESIZE_SVGA;
  camera.jpeg_quality = 12;
  camera.fb_count = 1;
  camera.fb_location = CAMERA_FB_IN_PSRAM;
  camera.grab_mode = CAMERA_GRAB_WHEN_EMPTY;

  const esp_err_t result = esp_camera_init(&camera);
  if (result != ESP_OK) {
    Serial.printf("ERROR: Camera initialization failed (0x%x). Check pinout and ribbon.\n",
                  static_cast<unsigned>(result));
    return false;
  }
  sensor_t* sensor = esp_camera_sensor_get();
  if (sensor) Serial.printf("Camera sensor PID: 0x%04x\n", sensor->id.PID);
  return true;
}

void capture(bool sendImage) {
  camera_fb_t* frame = esp_camera_fb_get();
  if (!frame) {
    Serial.println("ERROR: Camera capture failed.");
    return;
  }
  if (frame->format != PIXFORMAT_JPEG || !frame->buf || frame->len == 0) {
    Serial.println("ERROR: Camera returned an invalid JPEG frame.");
  } else if (sendImage) {
    Serial.printf("CEKRIR_JPEG %u\n", static_cast<unsigned>(frame->len));
    Serial.write(frame->buf, frame->len);
    Serial.flush();
    Serial.println("\nCEKRIR_END");
  } else {
    Serial.printf("Capture OK: %u x %u, %u bytes\n", static_cast<unsigned>(frame->width),
                  static_cast<unsigned>(frame->height), static_cast<unsigned>(frame->len));
  }
  esp_camera_fb_return(frame);
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.printf("Camera diagnostic: %s\n", camera_pins::kName);
  cameraReady = startCamera();
  if (cameraReady) Serial.println("READY: Capturing every 3 seconds; send c for a JPEG.");
}

void loop() {
  if (!cameraReady) {
    delay(1000);
    return;
  }
  if (Serial.available() && Serial.read() == 'c') capture(true);
  if (millis() - lastCheck >= kCheckIntervalMs) {
    lastCheck = millis();
    capture(false);
  }
  delay(10);
}
