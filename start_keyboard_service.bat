@echo off
REM Kannada Smart Keyboard - Quick Launcher
REM ========================================

echo.
echo ======================================================================
echo    Kannada Smart Keyboard Service - Quick Launcher
echo ======================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

echo [1/3] Checking dependencies...
python -c "import win32api, pynput" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARNING] Some dependencies are missing
    echo Installing required packages...
    echo.
    pip install pywin32 pynput pyperclip
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        echo Please run manually: pip install pywin32 pynput pyperclip
        pause
        exit /b 1
    )
)

echo [2/3] Verifying setup...
python test_setup.py
if errorlevel 1 (
    echo.
    echo [WARNING] Some tests failed, but service may still work
    echo.
)

echo.
echo [3/3] Starting Smart Keyboard Service...
echo.
echo ======================================================================
echo INSTRUCTIONS:
echo   - Service will load NLP models (takes 10-15 seconds)
echo   - Once running, type Kannada text in any app
echo   - Press Space after each word to trigger auto-correct
echo   - Press Ctrl+Shift+K to toggle on/off
echo   - Press Ctrl+C here to stop the service
echo ======================================================================
echo.
pause

python smart_keyboard_service.py

echo.
echo ======================================================================
echo Service stopped. Thank you for using Kannada Smart Keyboard!
echo ======================================================================
pause
