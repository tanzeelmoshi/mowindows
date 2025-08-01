@echo off
REM MoScraper Setup Script for Windows
REM This script sets up the complete environment for MoScraper

echo 🚀 MoScraper Setup for Windows
echo ===============================

cd /d "%~dp0"
echo 📍 Working in: %CD%

echo 🔍 Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.8+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

python --version
echo ✅ Python found

echo 🔧 Creating virtual environment...
if exist ".venv" (
    echo Virtual environment already exists
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo 🔧 Activating virtual environment...
call .venv\Scripts\activate.bat

echo 📦 Installing dependencies...
pip install --upgrade pip

REM Check if Windows-specific requirements exist
if exist "requirements.windows.txt" (
    echo Installing Windows-optimized requirements...
    pip install -r requirements.windows.txt
) else (
    echo Installing standard requirements...
    pip install -r requirements.txt
)

if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo 🌐 Checking Chrome installation...
REM Try common Chrome install locations if not found in PATH
where chrome >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
        echo ✅ Chrome found in Program Files
        set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
    ) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
        echo ✅ Chrome found in Program Files (x86)
        set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ) else (
        echo ⚠️  Chrome not found in PATH or default locations. Please install Google Chrome for the best experience.
        echo You can download it from: https://www.google.com/chrome/
    )
) else (
    echo ✅ Chrome found in PATH
)

echo.
echo ✅ Setup completed successfully!
echo 🎯 You can now run MoScraper by double-clicking start.bat
echo.

REM Start Streamlit on localhost:8501 automatically after setup
streamlit run app.py --server.port=8501 --server.address=localhost --server.headless=true
exit /b 0
