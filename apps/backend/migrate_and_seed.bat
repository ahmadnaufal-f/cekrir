@echo off
setlocal
cd /d "%~dp0..\.."
set "PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Backend Python was not found: %PYTHON%
    pause
    exit /b 1
)
echo Applying database migrations and seed data...
"%PYTHON%" -m alembic -c "%~dp0alembic.ini" upgrade head
if errorlevel 1 (
    echo Migration failed. Check the PostgreSQL connection and try again.
    pause
    exit /b 1
)
echo.
pause
