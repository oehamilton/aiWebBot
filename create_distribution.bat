@echo off
REM Script to create a distributable package for Windows

echo ========================================
echo Creating Windows Distribution Package
echo ========================================
echo.

set DIST_DIR=AIWebBot_Windows
set VERSION=0.1.0

REM Clean previous distribution
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"

echo [1/5] Copying application files...
xcopy /E /I /Y src "%DIST_DIR%\src"
xcopy /E /I /Y config "%DIST_DIR%\config"
copy /Y pyproject.toml "%DIST_DIR%\"
copy /Y requirements.txt "%DIST_DIR%\"
copy /Y README.md "%DIST_DIR%\"
copy /Y LICENSE "%DIST_DIR%\"
copy /Y INSTALL_WINDOWS.md "%DIST_DIR%\"

echo [2/5] Copying launcher scripts...
copy /Y launcher.bat "%DIST_DIR%\"
copy /Y launcher_no_gui.bat "%DIST_DIR%\"
copy /Y setup_windows.bat "%DIST_DIR%\"

echo [3/5] Creating README for distribution...
(
echo AI Web Bot v%VERSION% - Windows Distribution
echo.
echo QUICK START:
echo 1. Run setup_windows.bat to install dependencies
echo 2. Edit config\my_config.json with your settings
echo 3. Run launcher.bat to start the application
echo.
echo For detailed instructions, see INSTALL_WINDOWS.md
) > "%DIST_DIR%\QUICKSTART.txt"

echo [4/5] Creating ZIP archive...
if exist "%DIST_DIR%_v%VERSION%.zip" del "%DIST_DIR%_v%VERSION%.zip"
powershell -Command "Compress-Archive -Path '%DIST_DIR%' -DestinationPath '%DIST_DIR%_v%VERSION%.zip' -Force"

echo [5/5] Cleaning up...
echo.

echo ========================================
echo Distribution created successfully!
echo ========================================
echo.
echo Package: %DIST_DIR%_v%VERSION%.zip
echo.
echo Contents:
echo   - Application source code
echo   - Configuration files
echo   - Windows launcher scripts
echo   - Setup script
echo   - Documentation
echo.
echo To distribute:
echo   1. Share the ZIP file
echo   2. Recipients need Python 3.9+ installed
echo   3. Recipients extract and run setup_windows.bat
echo.
echo NOTE: This distribution REQUIRES Python to be installed.
echo For a standalone .exe (no Python required), use build_standalone_gui.py
echo.
pause

