#pragma once

#include <cstdint>

// Copy to config.h (gitignored), then set values for your device and network.
namespace config {
constexpr char kWifiSsid[] = "CHANGE_ME";
constexpr char kWifiPassword[] = "CHANGE_ME";
constexpr char kApiBaseUrl[] = "https://api.example.invalid/api/v1";
constexpr char kIngestApiKey[] = "CHANGE_ME";  // Match backend CEKRIR_INGEST_API_KEY.
constexpr char kCameraId[] = "esp32-front-door";
constexpr char kCourier[] = "jne";  // The barcode alone does not identify a courier.

// PEM root CA that signs your HTTPS API certificate. Never disable verification.
constexpr char kApiRootCa[] = "";
constexpr bool kAllowPlainHttp = false;  // Explicit opt-in for a trusted development LAN only.

constexpr uint32_t kScanIntervalMs = 3000;
constexpr uint32_t kDetectionCooldownMs = 15000;
constexpr uint32_t kMaxRetryMs = 60000;
constexpr uint32_t kWifiRetryMs = 15000;
constexpr uint16_t kRequestTimeoutMs = 15000;
constexpr int kJpegQuality = 12;  // Lower values produce better quality / larger frames.
}  // namespace config
