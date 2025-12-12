@echo off
REM Windows setup script for AI Web Bot
REM This installs dependencies and sets up the application

echo ========================================
echo AI Web Bot - Windows Setup
echo ========================================
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.9 or later from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Checking Python version...
python --version

echo.
echo [2/4] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -e .

echo.
echo [3/4] Installing Playwright browsers...
python -m playwright install chromium

echo.
echo [4/4] Creating default configuration...
if not exist "config\my_config.json" (
    python -m aiwebbot.main --generate-config config\my_config.json
    echo Default configuration created at config\my_config.json
) else (
    echo Configuration file already exists.
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit config\my_config.json with your settings
echo 2. Set GROK_API_KEY environment variable (optional)
echo 3. Run launcher.bat to start the application
echo.
pause

