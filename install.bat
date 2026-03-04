@echo off
REM Quick installer for WAN Video Generator (run from source)
REM This sets up the Python environment and downloads the model

echo ============================================
echo  WAN Video Generator — Setup
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10+ is required.
    echo Download from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip not found. Reinstall Python with pip enabled.
    pause
    exit /b 1
)

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created.
)

REM Activate
call venv\Scripts\activate.bat

REM Install PyTorch with CUDA support
echo.
echo Installing PyTorch with CUDA 12.4 support...
echo (This may take a while depending on your internet speed)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

REM Install other dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo ============================================
echo  Setup Complete!
echo ============================================
echo.
echo To run the application:
echo   1. Double-click run.bat
echo   OR
echo   2. Open terminal here and run:
echo      venv\Scripts\activate
echo      python main.py
echo.
echo On first generation, the WAN2.1 model will be
echo downloaded automatically (~25GB). Make sure you
echo have internet for that first download.
echo After that, everything works fully offline.
echo.
pause
