@echo off
REM 📦 Create Windows Deployment Package
REM This script creates a portable package for Windows deployment

echo 📦 Creating Windows Deployment Package
echo =======================================

REM Create deployment folder
if exist "MoScraper-Windows" rmdir /s /q "MoScraper-Windows"
mkdir "MoScraper-Windows"

echo 📁 Copying essential files...

REM Copy main files
copy "app.py" "MoScraper-Windows\"
copy "config.py" "MoScraper-Windows\"
copy "requirements.windows.txt" "MoScraper-Windows\"
copy "start.bat" "MoScraper-Windows\"
copy "setup.bat" "MoScraper-Windows\"
copy "🚀 Launch MoScraper.bat" "MoScraper-Windows\"
copy "README.md" "MoScraper-Windows\"
copy "WINDOWS_SETUP.md" "MoScraper-Windows\"

REM Copy optional files if they exist
if exist "logo.png" copy "logo.png" "MoScraper-Windows\"
if exist "logo2.png" copy "logo2.png" "MoScraper-Windows\"
if exist ".env" copy ".env" "MoScraper-Windows\"

REM Create directories
mkdir "MoScraper-Windows\data"
mkdir "MoScraper-Windows\logs"
mkdir "MoScraper-Windows\temp"

REM Copy directory contents if they exist
if exist "data" xcopy "data\*" "MoScraper-Windows\data\" /E /I /Q
if exist "logs" xcopy "logs\*" "MoScraper-Windows\logs\" /E /I /Q

echo ✅ Deployment package created in: MoScraper-Windows\
echo.
echo 📋 To deploy on Windows:
echo    1. Copy the entire 'MoScraper-Windows' folder to the target machine
echo    2. Double-click '🚀 Launch MoScraper.bat' on the Windows machine
echo    3. That's it! The app will auto-setup and start
echo.
echo 🎯 Windows deployment package ready!
pause
