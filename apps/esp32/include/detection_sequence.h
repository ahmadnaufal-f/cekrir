#pragma once

#include <cstdint>

// Start with one beep and a red light, then beep twice after three seconds.
class DetectionSequence {
 public:
  void start(uint32_t now) {
    started_ = now;
    active_ = true;
  }

  bool active() const { return active_; }

  bool red(uint32_t now) const { return active_ && elapsed(now) < 3000; }

  bool beep(uint32_t now) const {
    if (!active_) return false;
    const uint32_t ms = elapsed(now);
    return ms < 200 || (ms >= 3000 && ms < 3200) || (ms >= 3400 && ms < 3600);
  }

  bool finishIfDue(uint32_t now) {
    if (!active_ || elapsed(now) < 3600) return false;
    active_ = false;
    return true;
  }

 private:
  uint32_t elapsed(uint32_t now) const { return now - started_; }
  uint32_t started_ = 0;
  bool active_ = false;
};
