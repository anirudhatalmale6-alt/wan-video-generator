@echo off
REM Build WAN Video Generator into a standalone Windows executable
REM Requires: Python 3.10+, pip, PyInstaller

echo ============================================
echo  WAN Video Generator — Build Script
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

REM Create virtual environment if not exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Build executable
echo.
echo Building executable (this may take a few minutes)...
pyinstaller ^
    --name "WAN Video Generator" ^
    --windowed ^
    --onedir ^
    --icon assets\icon.ico ^
    --add-data "assets;assets" ^
    --hidden-import torch ^
    --hidden-import diffusers ^
    --hidden-import transformers ^
    --hidden-import accelerate ^
    --hidden-import safetensors ^
    --hidden-import sentencepiece ^
    --hidden-import imageio ^
    --hidden-import imageio_ffmpeg ^
    --hidden-import cv2 ^
    --hidden-import PIL ^
    --hidden-import PyQt6 ^
    --collect-all torch ^
    --collect-all diffusers ^
    --collect-all transformers ^
    --collect-all tokenizers ^
    --collect-all accelerate ^
    --noconfirm ^
    main.py

echo.
if errorlevel 1 (
    echo BUILD FAILED. Check errors above.
) else (
    echo BUILD SUCCESSFUL!
    echo Executable is in: dist\WAN Video Generator\
    echo.
    echo IMPORTANT: The model weights are NOT included in the build.
    echo On first run, the app will download them (~25GB per model).
    echo Alternatively, place model files in:
    echo   %%USERPROFILE%%\.wan_video_generator\models\
)

echo.
pause
