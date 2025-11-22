@echo off
REM ============================================================================
REM Real-Time Kannada Spell Checker - Startup Script
REM ============================================================================
REM
REM This script starts the real-time spell checker with transparent overlay
REM for Notepad and Microsoft Word
REM
REM Requirements:
REM   - Python 3.7 or higher
REM   - Required packages (see README.md for installation)
REM
REM ============================================================================

title Real-Time Kannada Spell Checker

echo.
echo ================================================================================
echo   Real-Time Kannada Spell Checker - Startup
echo ================================================================================
echo.
echo Starting the service...
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Run the spell checker
python realtime_spell_checker.py

REM If service exits, show message
echo.
echo ================================================================================
echo   Service Stopped
echo ================================================================================
echo.
pause
