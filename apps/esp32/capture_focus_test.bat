@echo off
setlocal

set "PORT=COM10"
if not "%~1"=="" set "PORT=%~1"
set "PIO_PYTHON=%USERPROFILE%\.platformio\penv\Scripts\python.exe"
set "BACKEND_PYTHON=%~dp0..\backend\.venv\Scripts\python.exe"

if not exist "%PIO_PYTHON%" (
    echo PlatformIO Python was not found: %PIO_PYTHON%
    pause
    exit /b 1
)
if not exist "%BACKEND_PYTHON%" (
    echo Backend Python was not found: %BACKEND_PYTHON%
    echo Set up the backend environment before running this test.
    pause
    exit /b 1
)

:choose_folder
set "OUTPUT_DIR=%~dp0captures\focus-test-%RANDOM%-%RANDOM%"
if exist "%OUTPUT_DIR%" goto choose_folder
mkdir "%OUTPUT_DIR%"
if errorlevel 1 (
    echo Could not create the output folder.
    pause
    exit /b 1
)

echo This test captures at 10, 15, 20 and 30 cm and checks each image locally.
echo It requires the camera-check firmware. Close any serial monitor first.
echo Use the same flat label and indirect light for all four pictures.
echo Keep the whole barcode and some white space visible on each side.
echo Pictures will be saved in: %OUTPUT_DIR%
echo.

for %%D in (10 15 20 30) do (
    echo Place the barcode %%D cm from the lens and hold it still.
    echo Press any key when ready, then keep it still while the image is captured.
    pause >nul
    "%PIO_PYTHON%" "%~dp0tools\capture_camera_check.py" --port "%PORT%" --output "%OUTPUT_DIR%\barcode-%%Dcm.jpg"
    if errorlevel 1 (
        echo Capture failed. Check the USB port and camera-check firmware.
        pause
        exit /b 1
    )
    echo Checking the %%D cm image...
    "%BACKEND_PYTHON%" "%~dp0decode_barcode.py" "%OUTPUT_DIR%\barcode-%%Dcm.jpg" --enhance --decode-only
    echo.
)

echo Test finished. Compare the four images in: %OUTPUT_DIR%
echo If no barcode was read, inspect which photo has the sharpest narrow lines.
start "" "%OUTPUT_DIR%"
pause
