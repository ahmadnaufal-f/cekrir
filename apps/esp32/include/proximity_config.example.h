#pragma once

// Copy to proximity_config.h. Select GPIOs only after confirming your board pinout.
// HC-SR04 ECHO MUST go through a 5 V to 3.3 V level shifter or resistor divider.
namespace proximity_config {
constexpr int kTriggerPin = 41;  // Used in the separate sensor test; verify your board.
constexpr int kEchoPin = -1;     // Set to a verified free GPIO different from the buzzer.
constexpr int kBuzzerPin = 14;   // Used in the separate buzzer test.
constexpr int kRgbLedPin = 48;   // Common ESP32-S3 CAM WS2812 pin; verify your board.
constexpr bool kActiveBuzzer = true;
constexpr bool kActiveHigh = true;
constexpr float kTriggerDistanceCm = 10.0f;
constexpr float kReleaseDistanceCm = 15.0f;
constexpr unsigned long kSampleIntervalMs = 200;
}  // namespace proximity_config
