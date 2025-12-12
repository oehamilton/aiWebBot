@echo off
REM Windows batch launcher for AI Web Bot
REM This allows double-clicking to run the application

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.9 or later from https://www.python.org/
    pause
    exit /b 1
)

REM Run with GUI by default
python -m aiwebbot.main --gui

pause

