@echo off
setlocal

rem Change COM10 if your ESP32 uses another port, or pass the port as an argument.
set "PORT=COM10"
if not "%~1"=="" set "PORT=%~1"
set "PLATFORMIO=%USERPROFILE%\.platformio\penv\Scripts\platformio.exe"

if not exist "%PLATFORMIO%" (
    echo PlatformIO was not found: %PLATFORMIO%
    pause
    exit /b 1
)

if not exist "%~dp0include\wifi_camera_config.h" (
    echo Wi-Fi settings are missing: include\wifi_camera_config.h
    echo Follow the Wi-Fi camera setup in README.md first.
    pause
    exit /b 1
)

echo Building and uploading the Wi-Fi video firmware to %PORT%...
echo Keep the ESP32 connected until the upload finishes.
echo.
"%PLATFORMIO%" run --project-dir "%~dp0." --environment esp32_s3_cam_wifi_video --target upload --upload-port "%PORT%"
if errorlevel 1 (
    echo.
    echo Build or upload failed. Check the messages above, USB cable and COM port.
    echo Close any serial monitor before trying again.
    pause
    exit /b 1
)

echo.
echo Upload complete. Start the camera backend and open http://localhost:8001/camera/video
pause
