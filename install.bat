@echo off
setlocal enabledelayedexpansion
title OBS Camera Pro - Installer

echo ======================================================================
echo                OBS CAMERA PRO - WINDOWS INSTALLER
echo ======================================================================
echo.

cd /d "%~dp0"

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    if not exist "venv\Scripts\python.exe" (
        echo [ERROR] Python was not found in your PATH.
        echo Please install Python 3.12+ from python.org and check "Add Python to PATH".
        pause
        exit /b 1
    )
)

echo [*] Initializing virtual environment...
if not exist "venv\Scripts\python.exe" (
    python -m venv venv
)

echo [*] Installing / Upgrading pip dependencies...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt

echo [*] Checking MediaMTX binary...
if not exist "services\mediamtx\mediamtx.exe" (
    echo [*] Downloading MediaMTX for Windows AMD64...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/bluenviron/mediamtx/releases/download/v1.21.3/mediamtx_v1.21.3_windows_amd64.zip' -OutFile 'services\mediamtx\mediamtx.zip'; Expand-Archive -Path 'services\mediamtx\mediamtx.zip' -DestinationPath 'services\mediamtx' -Force; Remove-Item 'services\mediamtx\mediamtx.zip'"
)

echo.
echo ======================================================================
echo [SUCCESS] OBS Camera Pro installation complete!
echo You can now start the application anytime by double clicking:
echo run.bat
echo ======================================================================
pause

