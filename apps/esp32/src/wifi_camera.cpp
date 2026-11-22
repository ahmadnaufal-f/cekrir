#include <Arduino.h>
#include <ESPmDNS.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <WiFi.h>
#include <driver/gpio.h>
#include <esp_camera.h>

#include "camera_pins.h"
#include "detection_sequence.h"
#include "proximity_policy.h"

#if __has_include("proximity_config.h")
#include "proximity_config.h"
#else
#include "proximity_config.example.h"
#endif

#if __has_include("wifi_camera_config.h")
#include "wifi_camera_config.h"
#else
#include "wifi_camera_config.example.h"
#endif

namespace {
constexpr uint32_t kReconnectIntervalMs = 15000;
WebServer server(80);
bool cameraReady = false;
bool serverReady = false;
bool sensorReady = false;
bool buzzerOn = false;
bool lightRed = false;
uint32_t lastReconnect = 0;
uint32_t lastSensorSample = 0;
uint32_t successfulUploads = 0;
camera_fb_t* pendingFrame = nullptr;
DetectionSequence sequence;
ProximityPolicy proximity(proximity_config::kTriggerDistanceCm,
                          proximity_config::kReleaseDistanceCm);

bool safePin(int pin) {
  if (pin < 0 || !GPIO_IS_VALID_OUTPUT_GPIO(pin) || pin == 0 || pin == 3 ||
      pin == 19 || pin == 20 || (pin >= 26 && pin <= 37) || pin == 45 || pin == 46) return false;
  const int cameraPins[] = {camera_pins::kPwdn, camera_pins::kReset, camera_pins::kXclk,
                           camera_pins::kSda, camera_pins::kScl, camera_pins::kD0,
                           camera_pins::kD1, camera_pins::kD2, camera_pins::kD3,
                           camera_pins::kD4, camera_pins::kD5, camera_pins::kD6,
                           camera_pins::kD7, camera_pins::kVsync, camera_pins::kHref,
                           camera_pins::kPclk};
  for (int cameraPin : cameraPins) if (pin == cameraPin) return false;
  return true;
}

bool sensorPinsValid() {
  const int pins[] = {proximity_config::kTriggerPin, proximity_config::kEchoPin,
                      proximity_config::kBuzzerPin, proximity_config::kRgbLedPin};
  for (unsigned i = 0; i < 4; ++i) {
    if (!safePin(pins[i])) return false;
    for (unsigned j = 0; j < i; ++j) if (pins[i] == pins[j]) return false;
  }
  return proximity_config::kTriggerDistanceCm > 0 &&
         proximity_config::kReleaseDistanceCm > proximity_config::kTriggerDistanceCm &&
         proximity_config::kSampleIntervalMs >= 60;
}

void setBuzzer(bool enabled) {
  if (enabled == buzzerOn) return;
  buzzerOn = enabled;
  if (proximity_config::kActiveBuzzer) {
    digitalWrite(proximity_config::kBuzzerPin,
                 enabled == proximity_config::kActiveHigh ? HIGH : LOW);
  } else if (enabled) {
    tone(proximity_config::kBuzzerPin, 2000);
  } else {
    noTone(proximity_config::kBuzzerPin);
  }
}

void setLight(bool red) {
  if (red == lightRed) return;
  lightRed = red;
  rgbLedWrite(proximity_config::kRgbLedPin, red ? 32 : 0, red ? 0 : 32, 0);
}

float readDistanceCm() {
  digitalWrite(proximity_config::kTriggerPin, LOW);
  delayMicroseconds(2);
  digitalWrite(proximity_config::kTriggerPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(proximity_config::kTriggerPin, LOW);
  const unsigned long pulse = pulseIn(proximity_config::kEchoPin, HIGH, 30000);
  return pulse == 0 ? 0.0f : pulse * 0.0343f / 2.0f;
}

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
              "<p>Pictures are captured when the proximity sensor detects an object.</p>");
}

void health() {
  if (!authorize()) return;
  server.sendHeader("Cache-Control", "no-store");
  String result = String("{\"camera\":\"") + (cameraReady ? "ready" : "unavailable") +
                  "\",\"sensor\":\"" + (sensorReady ? "configured" : "unconfigured") + "\"}";
  server.send(cameraReady && sensorReady ? 200 : 503, "application/json", result);
}

void uploadFrame(camera_fb_t* frame) {
  if (!frame) return;
  if (WiFi.status() != WL_CONNECTED || !strlen(wifi_camera_config::kBackendUrl)) {
    Serial.println("Picture not uploaded: Wi-Fi or backend URL unavailable.");
    esp_camera_fb_return(frame);
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
  Serial.println("Mode: one picture per proximity detection.");
  if (!configured()) {
    Serial.println("ERROR: Set Wi-Fi and camera password in wifi_camera_config.h.");
    return;
  }
  cameraReady = startCamera();
  sensorReady = sensorPinsValid();
  if (sensorReady) {
    pinMode(proximity_config::kTriggerPin, OUTPUT);
    digitalWrite(proximity_config::kTriggerPin, LOW);
    pinMode(proximity_config::kEchoPin, INPUT);
    pinMode(proximity_config::kBuzzerPin, OUTPUT);
    digitalWrite(proximity_config::kBuzzerPin,
                 proximity_config::kActiveBuzzer && !proximity_config::kActiveHigh ? HIGH : LOW);
    rgbLedWrite(proximity_config::kRgbLedPin, 0, 32, 0);
    Serial.println("Proximity sensor ready.");
  } else {
    Serial.println("ERROR: Set distinct safe proximity, buzzer and LED pins in proximity_config.h.");
  }
  server.on("/", HTTP_GET, home);
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
  uint32_t now = millis();
  if (sequence.active()) {
    setLight(sequence.red(now));
    setBuzzer(sequence.beep(now));
    if (sequence.finishIfDue(now)) {
      setBuzzer(false);
      setLight(false);
      uploadFrame(pendingFrame);
      pendingFrame = nullptr;
    }
    delay(5);
    return;
  }

  if (sensorReady && now - lastSensorSample >= proximity_config::kSampleIntervalMs) {
    lastSensorSample = now;
    const float distance = readDistanceCm();
    if (proximity.update(distance)) {
      Serial.printf("Object detected at %.1f cm. Capturing picture.\n", distance);
      now = millis();
      sequence.start(now);
      setLight(true);
      setBuzzer(true);
      pendingFrame = cameraReady ? esp_camera_fb_get() : nullptr;
      if (!pendingFrame) Serial.println("Camera capture failed or camera unavailable.");
      return;
    }
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
