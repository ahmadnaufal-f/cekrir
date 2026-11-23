@echo off
setlocal

rem This receives a JPEG from the camera-check firmware over USB.
set "PORT=COM10"
if not "%~1"=="" set "PORT=%~1"
set "PYTHON=%USERPROFILE%\.platformio\penv\Scripts\python.exe"
set "OUTPUT=%~dp0captures\barcode-test.jpg"

echo ESP32 barcode image capture
echo Port: %PORT%
echo Place the barcode about 15 cm from the camera in a well-lit area.
echo Close the PlatformIO serial monitor before continuing.
echo.

if not exist "%PYTHON%" (
    echo PlatformIO Python was not found: %PYTHON%
    echo Install PlatformIO, then try again.
    pause
    exit /b 1
)

"%PYTHON%" -c "import serial" >nul 2>&1
if errorlevel 1 (
    echo The PlatformIO Python environment is missing pyserial.
    echo Install it using: "%PYTHON%" -m pip install pyserial
    pause
    exit /b 1
)

"%PYTHON%" "%~dp0tools\capture_camera_check.py" --port "%PORT%" --output "%OUTPUT%"
if errorlevel 1 (
    echo.
    echo Capture failed. Check the port, USB cable and camera-check firmware.
    echo This capture script does not upload firmware to the ESP32.
    pause
    exit /b 1
)

echo.
echo Saved: %OUTPUT%
echo Opening the image...
start "" "%OUTPUT%"
pause
