@echo off
setlocal

rem Change COM10 below if your ESP32 uses another port.
set "PORT=COM10"
if not "%~1"=="" set "PORT=%~1"
set "PYTHON=%USERPROFILE%\.platformio\penv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo PlatformIO Python was not found: %PYTHON%
    echo Install PlatformIO, then try again.
    pause
    exit /b 1
)

"%PYTHON%" "%~dp0tools\capture_camera_check.py" --port "%PORT%"
if errorlevel 1 (
    echo.
    echo Capture failed. Check the port and close any serial monitor.
    pause
    exit /b 1
)

echo.
echo Opening your picture...
start "" "%~dp0captures\camera-check.jpg"
echo Press any key to close this window.
pause >nul
