#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <esp_camera.h>
#include <time.h>

#include "camera_pins.h"
#include "scan_policy.h"

#if __has_include("config.h")
#include "config.h"
#else
#include "config.example.h"
#endif

namespace {
bool ready = false;
bool useTls = true;
uint32_t lastWifiAttempt = 0;
uint32_t lastScan = 0;
uint32_t lastClockNotice = 0;
uint32_t scanDelay = config::kScanIntervalMs;
String frameUrl;

bool validateConfig() {
  String base = config::kApiBaseUrl;
  useTls = base.startsWith("https://");
  if (String(config::kWifiSsid).isEmpty() || String(config::kWifiSsid) == "CHANGE_ME" ||
      base.indexOf(".invalid") >= 0 || !scan_policy::validCourier(config::kCourier) ||
      strlen(config::kCameraId) == 0 || strlen(config::kCameraId) > 100 ||
      config::kScanIntervalMs < 1000 || config::kMaxRetryMs < config::kScanIntervalMs ||
      config::kDetectionCooldownMs < config::kScanIntervalMs ||
      config::kDetectionCooldownMs > config::kMaxRetryMs || config::kJpegQuality < 0 ||
      config::kJpegQuality > 63) {
    Serial.println("Set valid Wi-Fi, API, camera, courier and timing values in include/config.h.");
    return false;
  }
  if ((!useTls && (!base.startsWith("http://") || !config::kAllowPlainHttp)) ||
      (useTls && strlen(config::kApiRootCa) == 0)) {
    Serial.println("HTTPS requires a root CA. Plain HTTP requires explicit development opt-in.");
    return false;
  }
  while (base.endsWith("/")) base.remove(base.length() - 1);
  frameUrl = base + "/detections/frame?courier=" +
             scan_policy::urlEncode(config::kCourier).c_str() + "&camera_id=" +
             scan_policy::urlEncode(config::kCameraId).c_str();
  return true;
}

bool startCamera() {
  if (!psramFound()) {
    Serial.println("PSRAM is required. Check board profile and hardware.");
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
  camera.frame_size = FRAMESIZE_SVGA;  // 800 x 600; tune against actual labels.
  camera.jpeg_quality = config::kJpegQuality;
  camera.fb_count = 1;
  camera.fb_location = CAMERA_FB_IN_PSRAM;
  camera.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  const esp_err_t result = esp_camera_init(&camera);
  if (result != ESP_OK) {
    Serial.printf("Camera initialization failed (0x%x). Check camera ribbon and board profile.\n",
                  static_cast<unsigned>(result));
    return false;
  }
  return true;
}

struct UploadResult {
  bool accepted = false;
  int detected = 0;
};

UploadResult sendFrame(camera_fb_t* frame) {
  WiFiClient plainClient;
  WiFiClientSecure secureClient;
  HTTPClient http;
  if (useTls) {
    secureClient.setCACert(config::kApiRootCa);
    secureClient.setHandshakeTimeout(10);
    if (!http.begin(secureClient, frameUrl)) return {};
  } else {
    if (!http.begin(plainClient, frameUrl)) return {};
  }
  http.setConnectTimeout(5000);
  http.setTimeout(config::kRequestTimeoutMs);
  http.setReuse(false);
  http.useHTTP10(true);  // A bounded Content-Length response, without chunked transfer.
  http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS);
  http.addHeader("Content-Type", "image/jpeg");
  if (strlen(config::kIngestApiKey) > 0) http.addHeader("X-Ingest-Key", config::kIngestApiKey);
  const int status = http.POST(frame->buf, frame->len);
  UploadResult result;
  if (status == 200 && http.getSize() > 0 && http.getSize() <= 2048) {
    JsonDocument response;
    const DeserializationError error = deserializeJson(response, http.getString());
    const int count = response["detected_count"] | -1;
    if (!error && count >= 0 && count <= 1) {
      result = {true, count};
      if (response["ambiguous"] | false) {
        Serial.println("Multiple barcode candidates: move one label into the camera view.");
      }
    }
  }
  if (!result.accepted) Serial.printf("Frame submission failed (HTTP %d); backing off.\n", status);
  http.end();
  return result;
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.printf("Cekrir camera: %s\n", camera_pins::kName);
  if (!validateConfig() || !startCamera()) return;
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);
  WiFi.begin(config::kWifiSsid, config::kWifiPassword);
  if (useTls) configTime(0, 0, "pool.ntp.org", "time.cloudflare.com");
  lastWifiAttempt = millis();
  lastScan = millis() - config::kScanIntervalMs;
  ready = true;
}

void loop() {
  delay(20);
  if (!ready) return;
  const uint32_t now = millis();
  if (WiFi.status() != WL_CONNECTED) {
    if (scan_policy::elapsed(now, lastWifiAttempt, config::kWifiRetryMs)) {
      lastWifiAttempt = now;
      WiFi.reconnect();
      Serial.println("Reconnecting to Wi-Fi.");
    }
    return;
  }
  // TLS certificate validation needs a real clock; never bypass it if NTP fails.
  if (useTls && time(nullptr) < 1700000000) {
    if (scan_policy::elapsed(now, lastClockNotice, 15000)) {
      lastClockNotice = now;
      Serial.println("Waiting for NTP time synchronization before HTTPS submissions.");
    }
    return;
  }
  if (!scan_policy::elapsed(now, lastScan, scanDelay)) return;

  // With one buffer the driver may hold a frame from the previous cooldown.
  // Drain it, then request a newly captured frame for this submission.
  camera_fb_t* frame = esp_camera_fb_get();
  if (frame) {
    esp_camera_fb_return(frame);
    frame = esp_camera_fb_get();
  }
  if (!frame) {
    Serial.println("Camera capture failed; backing off.");
    scanDelay = scan_policy::retryDelay(scanDelay, config::kMaxRetryMs);
    lastScan = millis();
    return;
  }
  UploadResult result;
  if (frame->format == PIXFORMAT_JPEG && frame->len <= scan_policy::kMaxFrameBytes) {
    result = sendFrame(frame);
  } else {
    Serial.println("Frame is not JPEG or exceeds 512 KiB; reduce image size / JPEG quality.");
  }
  esp_camera_fb_return(frame);
  if (result.accepted) {
    scanDelay = result.detected ? config::kDetectionCooldownMs : config::kScanIntervalMs;
    Serial.printf("Frame accepted; %d barcode candidate(s) registered.\n", result.detected);
  } else {
    scanDelay = scan_policy::retryDelay(scanDelay, config::kMaxRetryMs);
  }
  lastScan = millis();
}
