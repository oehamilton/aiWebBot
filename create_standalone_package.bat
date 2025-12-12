@echo off
REM Script to create a complete standalone package after building the executable

echo ========================================
echo Creating Standalone Package
echo ========================================
echo.

set PACKAGE_DIR=AIWebBot_Standalone
set VERSION=0.1.0

REM Check if executable exists
if not exist "dist\AIWebBot.exe" (
    echo ERROR: AIWebBot.exe not found in dist folder!
    echo Please run: python build_standalone.py first
    pause
    exit /b 1
)

REM Clean previous package
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%"

echo [1/4] Copying executable...
copy /Y "dist\AIWebBot.exe" "%PACKAGE_DIR%\"

echo [2/4] Copying configuration files...
if exist "dist\config" (
    xcopy /E /I /Y "dist\config" "%PACKAGE_DIR%\config"
) else (
    echo   Warning: config folder not found in dist
    if exist "config" (
        xcopy /E /I /Y "config" "%PACKAGE_DIR%\config"
    )
)

echo [3/4] Copying documentation...
copy /Y "INSTALL_WINDOWS.md" "%PACKAGE_DIR%\"
copy /Y "README.md" "%PACKAGE_DIR%\"
if exist "dist\README.txt" copy /Y "dist\README.txt" "%PACKAGE_DIR%\"

echo [4/4] Creating package README...
(
echo AI Web Bot v%VERSION% - Standalone Windows Application
echo.
echo ========================================
echo QUICK START
echo ========================================
echo.
echo 1. Extract this ZIP file to a folder
echo.
echo 2. Install Playwright browsers ^(required^):
echo    - Open Command Prompt in this folder
echo    - Run: playwright install chromium
echo    - Note: You need Python installed just for this step
echo      ^(or use the portable Python included if provided^)
echo.
echo 3. Edit config\my_config.json with your settings:
echo    - twitter_username
echo    - twitter_password
echo    - post_to_reply_ratio
echo    - cooldown settings
echo.
echo 4. Set GROK_API_KEY environment variable ^(optional^)
echo.
echo 5. Run AIWebBot.exe
echo.
echo ========================================
echo IMPORTANT NOTES
echo ========================================
echo.
echo - This is a standalone executable - Python is NOT required to run
echo - However, Playwright browsers must be installed ^(one-time setup^)
echo - Browser data is stored in: %%USERPROFILE%%\.aiwebbot\
echo - Logs are created in: logs\ folder
echo.
echo For detailed instructions, see INSTALL_WINDOWS.md
echo.
) > "%PACKAGE_DIR%\QUICKSTART.txt"

echo.
echo Creating ZIP archive...
if exist "%PACKAGE_DIR%_v%VERSION%.zip" del "%PACKAGE_DIR%_v%VERSION%.zip"
powershell -Command "Compress-Archive -Path '%PACKAGE_DIR%' -DestinationPath '%PACKAGE_DIR%_v%VERSION%.zip' -Force"

echo.
echo ========================================
echo Package created successfully!
echo ========================================
echo.
echo Package: %PACKAGE_DIR%_v%VERSION%.zip
echo.
echo Contents:
echo   - AIWebBot.exe ^(standalone executable^)
echo   - config\ folder
echo   - Documentation
echo.
echo This package does NOT require Python to run!
echo ^(But Playwright browsers still need to be installed^)
echo.
pause

