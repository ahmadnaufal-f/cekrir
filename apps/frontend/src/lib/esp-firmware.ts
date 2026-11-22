export interface EspFirmwareSettings {
  deviceId: string
  deviceKey: string
  wifiSsid: string
  wifiPassword: string
  apiBaseUrl: string
  rootCa: string
  courier: string
}

// Byte escapes prevent credentials from breaking out of a C++ string literal.
function cString(value: string): string {
  return Array.from(new TextEncoder().encode(value), (byte) =>
    byte >= 32 && byte <= 126 && byte !== 34 && byte !== 92
      ? String.fromCharCode(byte)
      : `\\${byte.toString(8).padStart(3, '0')}`,
  ).join('')
}

export function generateEspConfig(input: EspFirmwareSettings): string {
  const apiUrl = new URL(input.apiBaseUrl)
  if (apiUrl.protocol !== 'https:' || apiUrl.username || apiUrl.password || apiUrl.search || apiUrl.hash ||
      !apiUrl.pathname.replace(/\/$/, '').endsWith('/api/v1'))
    throw new Error('The API URL must be HTTPS and end in /api/v1.')
  if (!input.deviceId || !input.deviceKey || !input.wifiSsid || !input.rootCa.includes('BEGIN CERTIFICATE') ||
      !/^[a-z0-9_-]{2,32}$/.test(input.courier))
    throw new Error('Complete the device, Wi-Fi, certificate, and courier details.')
  const text = (value: string) => `"${cString(value)}"`
  return `#pragma once
#include <cstdint>
namespace config {
constexpr char kWifiSsid[] = ${text(input.wifiSsid)};
constexpr char kWifiPassword[] = ${text(input.wifiPassword)};
constexpr char kApiBaseUrl[] = ${text(input.apiBaseUrl.replace(/\/$/, ''))};
constexpr char kCameraId[] = ${text(input.deviceId)};
constexpr char kDeviceKey[] = ${text(input.deviceKey)};
constexpr char kCourier[] = ${text(input.courier)};
constexpr char kApiRootCa[] = ${text(input.rootCa)};
constexpr bool kAllowPlainHttp = false;
constexpr uint32_t kScanIntervalMs = 3000;
constexpr uint32_t kDetectionCooldownMs = 15000;
constexpr uint32_t kMaxRetryMs = 60000;
constexpr uint32_t kWifiRetryMs = 15000;
constexpr uint16_t kRequestTimeoutMs = 15000;
constexpr int kJpegQuality = 12;
}
`
}
