@echo off
setlocal
set "PORT=COM10"
if not "%~1"=="" set "PORT=%~1"
set "PLATFORMIO=%USERPROFILE%\.platformio\penv\Scripts\platformio.exe"

if not exist "%PLATFORMIO%" (
    echo PlatformIO was not found: %PLATFORMIO%
    pause
    exit /b 1
)

echo This uploads the buzzer test and replaces the firmware on the board.
echo First set a verified free GPIO in src\buzzer_test.cpp.
echo Building and uploading to %PORT%...
"%PLATFORMIO%" run --project-dir "%~dp0." --environment esp32_s3_cam_buzzer_test --target upload --upload-port "%PORT%"
if errorlevel 1 (
    echo Build or upload failed. Check the cable, COM port and build output.
    pause
    exit /b 1
)
echo Upload complete. The buzzer test starts after the board resets.
pause
