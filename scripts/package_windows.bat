@echo off
setlocal enabledelayedexpansion
title OBS Camera Pro - Windows Packager

echo ======================================================================
echo                OBS CAMERA PRO - WINDOWS PACKAGER
echo ======================================================================
echo.

cd /d "%~dp0\.."

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run install.bat first.
    pause
    exit /b 1
)

echo [*] Installing PyInstaller into virtual environment...
venv\Scripts\pip.exe install pyinstaller

echo [*] Building portable desktop executable...
venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed ^
    --name "OBSCameraPro" ^
    --add-data "apps/desktop/frontend;apps/desktop/frontend" ^
    --add-data "services/mediamtx;services/mediamtx" ^
    --paths "apps/desktop/backend" ^
    apps/desktop/backend/main.py

echo.
echo ======================================================================
echo [SUCCESS] Package created in dist\OBSCameraPro\
echo You can run dist\OBSCameraPro\OBSCameraPro.exe directly.
echo ======================================================================
pause

