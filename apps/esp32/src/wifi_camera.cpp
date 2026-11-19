#include <Arduino.h>
#include <ESPmDNS.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <WiFi.h>
#include <esp_camera.h>

#include "camera_pins.h"

#if __has_include("wifi_camera_config.h")
#include "wifi_camera_config.h"
#else
#include "wifi_camera_config.example.h"
#endif

namespace {
constexpr uint32_t kReconnectIntervalMs = 15000;
constexpr uint32_t kSendTimeoutMs = 15000;
#ifdef CEKRIR_VIDEO_MODE
constexpr uint32_t kUploadIntervalMs = 100;
#else
constexpr uint32_t kUploadIntervalMs = 1000;
#endif
WebServer server(80);
bool cameraReady = false;
bool serverReady = false;
uint32_t lastReconnect = 0;
uint32_t lastUpload = 0;
uint32_t successfulUploads = 0;

bool configured() {
  return strlen(wifi_camera_config::kWifiSsid) > 0 &&
         String(wifi_camera_config::kWifiSsid) != "CHANGE_ME" &&
         String(wifi_camera_config::kWifiPassword) != "CHANGE_ME" &&
         strlen(wifi_camera_config::kCameraUser) > 0 &&
         strlen(wifi_camera_config::kCameraPassword) >= 12 &&
         String(wifi_camera_config::kCameraPassword) != "CHANGE_ME";
}

bool startCamera() {
  if (!psramFound()) {
    Serial.println("ERROR: PSRAM not detected.");
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
#ifdef CEKRIR_VIDEO_MODE
  camera.frame_size = FRAMESIZE_QVGA;
#else
  // Smaller frames reduce camera buffer pressure while Wi-Fi is active.
  camera.frame_size = FRAMESIZE_VGA;
#endif
  camera.jpeg_quality = 12;
  camera.fb_count = 1;
  camera.fb_location = CAMERA_FB_IN_PSRAM;
  camera.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  const esp_err_t result = esp_camera_init(&camera);
  if (result != ESP_OK) {
    Serial.printf("ERROR: Camera initialization failed (0x%x).\n", static_cast<unsigned>(result));
    return false;
  }
  return true;
}

bool authorize() {
  if (server.authenticate(wifi_camera_config::kCameraUser, wifi_camera_config::kCameraPassword)) {
    return true;
  }
  server.requestAuthentication(BASIC_AUTH, "Cekrir camera", "Authentication required");
  return false;
}

void home() {
  if (!authorize()) return;
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "text/html; charset=utf-8",
              "<!doctype html><meta name=viewport content='width=device-width'>"
              "<title>Cekrir camera</title><h1>Cekrir camera</h1>"
              "<p><a href='/capture.jpg'>Take a picture</a></p>");
}

void capture() {
  if (!authorize()) return;
  if (!cameraReady) {
    server.send(503, "text/plain", "Camera is unavailable");
    return;
  }
  camera_fb_t* frame = esp_camera_fb_get();
  if (!frame) {
    server.send(503, "text/plain", "Camera capture failed");
    return;
  }
  if (frame->format != PIXFORMAT_JPEG || !frame->buf || frame->len == 0) {
    esp_camera_fb_return(frame);
    server.send(500, "text/plain", "Camera did not return a JPEG");
    return;
  }

  const size_t frameSize = frame->len;
  server.sendHeader("Cache-Control", "no-store");
  server.setContentLength(frameSize);
  server.send(200, "image/jpeg", "");
  WiFiClient client = server.client();
  size_t sent = 0;
  uint32_t lastProgress = millis();
  while (sent < frameSize && client.connected() && millis() - lastProgress < kSendTimeoutMs) {
    const size_t written = client.write(frame->buf + sent, frameSize - sent);
    if (written) {
      sent += written;
      lastProgress = millis();
    } else {
      delay(10);
    }
  }
  esp_camera_fb_return(frame);
  if (sent != frameSize) Serial.println("Picture transfer was interrupted.");
}

void health() {
  if (!authorize()) return;
  server.sendHeader("Cache-Control", "no-store");
  server.send(cameraReady ? 200 : 503, "application/json",
              cameraReady ? "{\"camera\":\"ready\"}" : "{\"camera\":\"unavailable\"}");
}

void uploadFrame() {
  if (!cameraReady || !strlen(wifi_camera_config::kBackendUrl)) return;
  camera_fb_t* frame = esp_camera_fb_get();
  if (!frame) {
    Serial.println("Backend upload: camera capture failed.");
    return;
  }
  if (frame->format != PIXFORMAT_JPEG || !frame->buf || frame->len == 0) {
    esp_camera_fb_return(frame);
    Serial.println("Backend upload: invalid camera frame.");
    return;
  }
  WiFiClient client;
  HTTPClient http;
  http.setConnectTimeout(2000);
  http.setTimeout(3000);
  if (http.begin(client, wifi_camera_config::kBackendUrl)) {
    http.setAuthorization(wifi_camera_config::kCameraUser, wifi_camera_config::kCameraPassword);
    http.addHeader("Content-Type", "image/jpeg");
    int result = http.POST(frame->buf, frame->len);
    if (result != 200) {
      Serial.printf("Backend upload failed: HTTP/error %d.\n", result);
    } else if (++successfulUploads == 1 || successfulUploads % 10 == 0) {
      Serial.printf("Backend upload OK (%lu pictures).\n", static_cast<unsigned long>(successfulUploads));
    }
    http.end();
  } else {
    Serial.println("Backend upload: invalid URL.");
  }
  esp_camera_fb_return(frame);
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.printf("Wi-Fi camera: %s\n", camera_pins::kName);
#ifdef CEKRIR_VIDEO_MODE
  Serial.println("Mode: video frames (320x240).");
#else
  Serial.println("Mode: one picture per second (640x480).");
#endif
  if (!configured()) {
    Serial.println("ERROR: Set Wi-Fi and camera password in wifi_camera_config.h.");
    return;
  }
  cameraReady = startCamera();
  server.on("/", HTTP_GET, home);
  server.on("/capture.jpg", HTTP_GET, capture);
  server.on("/health", HTTP_GET, health);
  server.onNotFound([]() {
    if (authorize()) server.send(404, "text/plain", "Not found");
  });
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(wifi_camera_config::kHostname);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  WiFi.begin(wifi_camera_config::kWifiSsid, wifi_camera_config::kWifiPassword);
  lastReconnect = millis();
  Serial.println("Connecting to Wi-Fi...");
}

void loop() {
  if (!configured()) {
    delay(1000);
    return;
  }
  if (WiFi.status() == WL_CONNECTED) {
    if (!serverReady) {
      server.begin();
      if (MDNS.begin(wifi_camera_config::kHostname)) {
        MDNS.addService("http", "tcp", 80);
        Serial.printf("Local address: http://%s.local/\n", wifi_camera_config::kHostname);
      } else {
        Serial.println("Local name unavailable; use the IP address below.");
      }
      Serial.print("Camera IP: http://");
      Serial.println(WiFi.localIP());
      serverReady = true;
    }
    server.handleClient();
    if (millis() - lastUpload >= kUploadIntervalMs) {
      lastUpload = millis();
      uploadFrame();
    }
  } else {
    if (serverReady) {
      server.stop();
      MDNS.end();
      serverReady = false;
      Serial.println("Wi-Fi disconnected.");
    }
    if (millis() - lastReconnect >= kReconnectIntervalMs) {
      lastReconnect = millis();
      WiFi.reconnect();
      Serial.println("Reconnecting to Wi-Fi...");
    }
    delay(20);
  }
}
