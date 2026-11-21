#pragma once

#include <cstdint>

// Two near readings trigger once; three clear/invalid readings rearm the sensor.
class ProximityPolicy {
 public:
  explicit ProximityPolicy(float triggerCm, float releaseCm)
      : triggerCm_(triggerCm), releaseCm_(releaseCm) {}

  bool update(float distanceCm) {
    if (distanceCm > 0 && distanceCm <= triggerCm_) {
      clearCount_ = 0;
      if (nearCount_ < 2) ++nearCount_;
      if (!detected_ && nearCount_ >= 2) {
        detected_ = true;
        return true;
      }
    } else if (distanceCm <= 0 || distanceCm >= releaseCm_) {
      nearCount_ = 0;
      if (clearCount_ < 3) ++clearCount_;
      if (clearCount_ >= 3) detected_ = false;
    } else {
      nearCount_ = 0;
      clearCount_ = 0;
    }
    return false;
  }

 private:
  float triggerCm_;
  float releaseCm_;
  uint8_t nearCount_ = 0;
  uint8_t clearCount_ = 0;
  bool detected_ = false;
};
