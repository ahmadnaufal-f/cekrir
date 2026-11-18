#pragma once

// Pin assignments follow Espressif's CameraWebServer profiles. A different
// ESP32/S3 camera board needs its own mapping; the chip name is not a pinout.
namespace camera_pins {
#if (defined(CEKRIR_CAMERA_XIAO_S3) + defined(CEKRIR_CAMERA_AI_THINKER) + \
     defined(CEKRIR_CAMERA_ESP32_S3_CAM)) > 1
#error "Select one camera board profile"
#elif defined(CEKRIR_CAMERA_ESP32_S3_CAM)
// Common ESP32-S3 CAM N16R8 pinout; verify against the actual board.
constexpr int kPwdn = -1, kReset = -1, kXclk = 15, kSda = 4, kScl = 5;
constexpr int kD0 = 11, kD1 = 9, kD2 = 8, kD3 = 10;
constexpr int kD4 = 12, kD5 = 18, kD6 = 17, kD7 = 16;
constexpr int kVsync = 6, kHref = 7, kPclk = 13;
constexpr const char* kName = "ESP32-S3 CAM N16R8 (candidate pinout)";
#elif defined(CEKRIR_CAMERA_XIAO_S3)
constexpr int kPwdn = -1, kReset = -1, kXclk = 10, kSda = 40, kScl = 39;
constexpr int kD0 = 15, kD1 = 17, kD2 = 18, kD3 = 16;
constexpr int kD4 = 14, kD5 = 12, kD6 = 11, kD7 = 48;
constexpr int kVsync = 38, kHref = 47, kPclk = 13;
constexpr const char* kName = "Seeed XIAO ESP32S3 Sense";
#elif defined(CEKRIR_CAMERA_AI_THINKER)
constexpr int kPwdn = 32, kReset = -1, kXclk = 0, kSda = 26, kScl = 27;
constexpr int kD0 = 5, kD1 = 18, kD2 = 19, kD3 = 21;
constexpr int kD4 = 36, kD5 = 39, kD6 = 34, kD7 = 35;
constexpr int kVsync = 25, kHref = 23, kPclk = 22;
constexpr const char* kName = "AI Thinker ESP32-CAM";
#else
#error "Select a supported camera environment in platformio.ini"
#endif
}  // namespace camera_pins
