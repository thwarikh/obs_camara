@echo off
setlocal enabledelayedexpansion
title OBS Camera Pro - Control Center

echo ======================================================================
echo                     OBS CAMERA PRO - STARTUP
echo ======================================================================
echo.

cd /d "%~dp0"

:: 1. Check Python environment
if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
    echo [OK] Using virtual environment Python.
) else (
    echo [*] Virtual environment not found. Searching for system Python...
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        echo [*] Creating virtual environment 'venv'...
        python -m venv venv
        set "PY_EXE=venv\Scripts\python.exe"
    ) else (
        echo [ERROR] Python 3.12+ is not installed or not in PATH.
        echo Please install Python 3.12 or higher and re-run.
        pause
        exit /b 1
    )
)

:: 2. Check dependencies
if not exist "venv\Lib\site-packages\fastapi" (
    echo [*] Installing required backend dependencies...
    "%PY_EXE%" -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: 3. Check MediaMTX
if not exist "services\mediamtx\mediamtx.exe" (
    echo [*] Downloading MediaMTX streaming server...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/bluenviron/mediamtx/releases/download/v1.21.3/mediamtx_v1.21.3_windows_amd64.zip' -OutFile 'services\mediamtx\mediamtx.zip'; Expand-Archive -Path 'services\mediamtx\mediamtx.zip' -DestinationPath 'services\mediamtx' -Force; Remove-Item 'services\mediamtx\mediamtx.zip'"
    if not exist "services\mediamtx\mediamtx.exe" (
        echo [WARNING] MediaMTX binary download failed.
    )
)

:: 4. Start MediaMTX streaming server in background
echo [*] Launching MediaMTX streaming server (WebRTC WHEP: 8889, RTSP: 8554)...
start "OBS Camera Pro - MediaMTX" /B "services\mediamtx\mediamtx.exe" "services\mediamtx\mediamtx.yml"

:: 5. Open browser dashboard after short pause
start "" "http://127.0.0.1:8765"

:: 6. Launch FastAPI Desktop Backend
echo [*] Starting OBS Camera Pro Desktop Backend on http://0.0.0.0:8765 ...
echo [*] Press Ctrl+C to stop all services.
echo.

set "PYTHONPATH=apps\desktop\backend"
"%PY_EXE%" -m uvicorn main:app --host 0.0.0.0 --port 8765 --app-dir apps\desktop\backend

:: 7. Cleanup
echo.
echo [*] Shutting down MediaMTX process...
taskkill /F /IM mediamtx.exe >nul 2>&1
echo [OK] Services stopped cleanly.
pause

