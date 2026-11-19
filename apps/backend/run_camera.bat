@echo off
setlocal
set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Backend Python was not found: %PYTHON%
    echo Install the backend requirements first.
    pause
    exit /b 1
)
echo Starting the camera server. Keep this window open.
"%PYTHON%" "%~dp0run_camera.py"
echo.
echo The camera server has stopped.
pause
