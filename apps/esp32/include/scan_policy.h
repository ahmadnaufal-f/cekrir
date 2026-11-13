#pragma once

#include <cstdint>
#include <string>

namespace scan_policy {
constexpr unsigned kMaxFrameBytes = 512 * 1024;

inline bool elapsed(uint32_t now, uint32_t since, uint32_t interval) {
  return static_cast<uint32_t>(now - since) >= interval;
}

inline uint32_t retryDelay(uint32_t current, uint32_t maximum) {
  return current >= maximum / 2 ? maximum : current * 2;
}

inline bool validCourier(const std::string& value) {
  if (value.size() < 2 || value.size() > 32) return false;
  for (const unsigned char ch : value) {
    if (!((ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '_' || ch == '-')) {
      return false;
    }
  }
  return true;
}

inline std::string urlEncode(const std::string& value) {
  constexpr char hex[] = "0123456789ABCDEF";
  std::string result;
  for (const unsigned char ch : value) {
    if ((ch >= 'a' && ch <= 'z') || (ch >= 'A' && ch <= 'Z') ||
        (ch >= '0' && ch <= '9') || ch == '-' || ch == '_' || ch == '.' || ch == '~') {
      result += ch;
    } else {
      result += '%';
      result += hex[ch >> 4];
      result += hex[ch & 15];
    }
  }
  return result;
}
}  // namespace scan_policy
