@echo off
REM Helper script to install Playwright browsers
REM This is needed even for standalone executables

echo ========================================
echo Installing Playwright Browsers
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not found in PATH.
    echo.
    echo Playwright browsers require Python to install.
    echo.
    echo Options:
    echo 1. Install Python 3.9+ from https://www.python.org/
    echo 2. Use portable Python ^(if provided in package^)
    echo.
    echo After Python is installed, run this script again.
    pause
    exit /b 1
)

echo Python found. Installing Playwright browsers...
echo This may take a few minutes...
echo.

python -m playwright install chromium

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install Playwright browsers.
    echo Make sure you have internet connection.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Playwright browsers have been installed.
echo You can now run AIWebBot.exe
echo.
pause

