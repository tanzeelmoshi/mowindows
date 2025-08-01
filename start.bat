@echo off
REM MoScraper One-Click Launcher for Windows
REM This script automatically handles setup AND starts the application

echo 🎯 MoScraper One-Click Launcher for Windows
echo ==========================================

cd /d "%~dp0"
echo 📍 Working in: %CD%

REM Function to check if setup is needed
if not exist ".venv" (
    goto :setup_needed
)

REM Activate venv and check for key packages
call .venv\Scripts\activate.bat
python -c "import streamlit, selenium, undetected_chromedriver" >nul 2>&1
if errorlevel 1 (
    goto :setup_needed
)
goto :start_app

:setup_needed
echo 🔧 First time setup detected - installing dependencies...
echo ⏳ This may take a few minutes...

REM Check if setup.bat exists, otherwise run pip directly
if exist "setup.bat" (
    call setup.bat
) else (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing dependencies...
    if exist "requirements.windows.txt" (
        pip install -r requirements.windows.txt
    ) else (
        pip install -r requirements.txt
    )
)

if errorlevel 1 (
    echo ❌ Setup failed! Please check the errors above.
    echo Logging error output to setup_error.log...
    echo See setup_error.log for details.
    REM Log the last 50 lines of the console to a file
    powershell -Command "Get-Content setup.bat | Select-Object -Last 50 | Out-File setup_error.log -Append"
    exit /b 1
)

echo ✅ Setup completed successfully!
goto :start_app

:start_app
echo.
echo 🌐 Starting MoScraper Application...
echo ==================================

REM Check if virtual environment exists
if not exist ".venv" (
    echo ❌ Virtual environment not found. Setup may have failed.
    pause
    exit /b 1
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Verify dependencies one more time
echo 🔍 Verifying dependencies...
python -c "import streamlit, selenium, undetected_chromedriver" >nul 2>&1
if errorlevel 1 (
    echo ❌ Missing dependencies. Please check your installation.
    pause
    exit /b 1
)

REM Set environment for local execution
set ENVIRONMENT=desktop
set BROWSER_MODE=local

echo.
echo 🎉 All systems ready! Launching MoScraper...
echo 🔗 The application will open in your default web browser
echo 🔍 Chrome browser will open locally on your machine for scraping
echo.
echo 📋 Features available:
echo    • Local Chrome browser execution
echo    • Session persistence
echo    • LinkedIn lead scraping
echo    • Email automation
echo    • AI-powered email generation
echo.
echo 💡 To stop the application, press Ctrl+C in this window
echo.
echo 🚀 Starting Streamlit...

REM Start the application
set PORT=8501
if not "%1"=="" set PORT=%1
streamlit run app.py --server.port=%PORT% --server.address=localhost --server.headless=true

echo.
echo 👋 MoScraper stopped. Thank you for using MoScraper!
pause
