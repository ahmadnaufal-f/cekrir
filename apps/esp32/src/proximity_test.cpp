#include <Arduino.h>
#include <driver/gpio.h>

#include "camera_pins.h"

// Set these to two different, verified free GPIO numbers for your board.
// HC-SR04 ECHO must be reduced to 3.3 V before it reaches an ESP32 pin.
constexpr int kTriggerPin = 41;
constexpr int kEchoPin = 14;
constexpr float kNearDistanceCm = 30.0f;
constexpr unsigned long kSampleIntervalMs = 500;
constexpr unsigned long kEchoTimeoutUs = 30000;

bool safePin(int pin) {
  // These restrictions do not replace checking the exact board's pinout.
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

bool validPins() {
  return safePin(kTriggerPin) && safePin(kEchoPin) && kTriggerPin != kEchoPin;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  if (!validPins()) {
    Serial.println("Set two different verified free GPIOs in proximity_test.cpp.");
    return;
  }
  pinMode(kTriggerPin, OUTPUT);
  digitalWrite(kTriggerPin, LOW);
  pinMode(kEchoPin, INPUT);
  Serial.println("Ultrasonic sensor test started.");
}

void loop() {
  if (!validPins()) {
    delay(1000);
    return;
  }

  digitalWrite(kTriggerPin, LOW);
  delayMicroseconds(2);
  digitalWrite(kTriggerPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(kTriggerPin, LOW);

  const unsigned long pulseUs = pulseIn(kEchoPin, HIGH, kEchoTimeoutUs);
  if (pulseUs == 0) {
    Serial.println("No echo received (object out of range or check wiring).");
  } else {
    const float distanceCm = pulseUs * 0.0343f / 2.0f;
    Serial.printf("Distance: %.1f cm - %s\n", distanceCm,
                  distanceCm <= kNearDistanceCm ? "object nearby" : "clear");
  }
  delay(kSampleIntervalMs);
}
