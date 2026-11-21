#include <Arduino.h>
#include <driver/gpio.h>

#include "camera_pins.h"

// Replace -1 with a verified free GPIO number on your exact board.
constexpr int kBuzzerPin = 14;
// Common ESP32-S3 CAM boards use GPIO48 for a WS2812 RGB LED. Verify your board.
constexpr int kRgbLedPin = 48;
constexpr uint8_t kLedBrightness = 32;
// true: active buzzer. false: passive buzzer, such as most KY-006 modules.
constexpr bool kActiveBuzzer = true;
constexpr bool kActiveHigh = true;  // Only used for an active buzzer.
constexpr unsigned long kIntervalMs = 2000;
constexpr unsigned long kBeepDurationMs = 200;
constexpr unsigned int kToneFrequencyHz = 2000;

bool safePin(int pin) {
  // Avoid camera, USB, boot strapping and the S3 flash/PSRAM bus pins. The
  // actual board can reserve further pins; check its schematic before wiring.
  if (pin < 0 || !GPIO_IS_VALID_OUTPUT_GPIO(pin) || pin == 0 || pin == 3 ||
      pin == 19 || pin == 20 || (pin >= 26 && pin <= 37) || pin == 45 || pin == 46) {
        Serial.printf("Pin %d is not safe for a buzzer. Avoid camera, USB, boot strapping and the S3 flash/PSRAM bus pins.\n", pin);
    return false;
  }
  const int cameraPins[] = {camera_pins::kPwdn, camera_pins::kReset, camera_pins::kXclk,
                            camera_pins::kSda, camera_pins::kScl, camera_pins::kD0,
                            camera_pins::kD1, camera_pins::kD2, camera_pins::kD3,
                            camera_pins::kD4, camera_pins::kD5, camera_pins::kD6,
                            camera_pins::kD7, camera_pins::kVsync, camera_pins::kHref,
                            camera_pins::kPclk};
  for (const int cameraPin : cameraPins) {
    if (pin == cameraPin) {
      Serial.printf("hihii %d is not safe for a buzzer. Avoid camera, USB, boot strapping and the S3 flash/PSRAM bus pins.\n", pin);
      return false;
    }
  }
  return true;
}

void setup() {
  Serial.begin(115200);
  if (!safePin(kBuzzerPin)) {
    Serial.println("Select a verified free GPIO in buzzer_test.cpp before wiring the buzzer.");
    return;
  }
  pinMode(kBuzzerPin, OUTPUT);
  digitalWrite(kBuzzerPin, kActiveBuzzer && !kActiveHigh ? HIGH : LOW);
  if (kRgbLedPin != kBuzzerPin && safePin(kRgbLedPin)) {
    rgbLedWrite(kRgbLedPin, 0, kLedBrightness, 0);
  } else {
    Serial.println("RGB LED pin is invalid or conflicts with the buzzer; LED disabled.");
  }
  Serial.println("Buzzer test: one short beep every two seconds.");
}

void loop() {
  if (!safePin(kBuzzerPin)) {
    delay(1000);
    return;
  }
  const bool ledReady = kRgbLedPin != kBuzzerPin && safePin(kRgbLedPin);
  if (ledReady) rgbLedWrite(kRgbLedPin, kLedBrightness, 0, 0);
  if (kActiveBuzzer) {
    digitalWrite(kBuzzerPin, kActiveHigh ? HIGH : LOW);
  } else {
    tone(kBuzzerPin, kToneFrequencyHz);
  }
  delay(kBeepDurationMs);
  if (kActiveBuzzer) {
    digitalWrite(kBuzzerPin, kActiveHigh ? LOW : HIGH);
  } else {
    noTone(kBuzzerPin);
  }
  if (ledReady) rgbLedWrite(kRgbLedPin, 0, kLedBrightness, 0);
  delay(kIntervalMs - kBeepDurationMs);
}
