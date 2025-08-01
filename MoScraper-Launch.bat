@echo off
REM 🚀 MoScraper Direct Launcher for Windows
REM Double-click this file to start MoScraper instantly!

cd /d "%~dp0"
call .venv\Scripts\activate.bat
streamlit run app.py --server.port=8501 --server.address=localhost --server.headless=true
exit /b 0
