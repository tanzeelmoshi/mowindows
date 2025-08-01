@echo off
REM 🚀 MoScraper Quick Launch for Windows
REM Double-click this file to start MoScraper instantly!

title MoScraper Quick Launch

echo 🚀 MoScraper Quick Launch for Windows
echo ====================================
echo.

REM Change to script directory
cd /d "%~dp0"
echo 📍 Working in: %CD%
echo.

REM Check Python installation
echo 🔍 Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! 
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    exit /b 1
)
python --version
echo ✅ Python found
echo.

REM Check Chrome installation
echo 🔍 Checking Chrome installation...
where chrome >nul 2>&1
if errorlevel 1 (
    REM Try common install locations
    if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
        set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
        echo ✅ Chrome found in Program Files
    ) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
        set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        echo ✅ Chrome found in Program Files (x86)
    ) else (
        echo ⚠️  Chrome not found. Please install Google Chrome.
    )
) else (
    echo ✅ Chrome found in PATH
)

REM Start MoScraper on localhost:8501
streamlit run app.py --server.port=8501 --server.address=localhost --server.headless=true
exit /b 0
