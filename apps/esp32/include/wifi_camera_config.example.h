#pragma once

// Copy to wifi_camera_config.h and edit the three values below.
// Use your router's 2.4 GHz Wi-Fi network.
namespace wifi_camera_config {
constexpr char kWifiSsid[] = "CHANGE_ME";
constexpr char kWifiPassword[] = "CHANGE_ME";
constexpr char kCameraUser[] = "camera";
constexpr char kCameraPassword[] = "CHANGE_ME";
constexpr char kHostname[] = "cekrir-camera";
// Replace with your PC's local IP address. Leave empty to disable uploads.
constexpr char kBackendUrl[] = "http://192.168.1.100:8001/camera/frame";
}  // namespace wifi_camera_config
