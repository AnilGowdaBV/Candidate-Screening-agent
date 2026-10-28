@echo off
title Candidate Screening Agent - First Time Setup
echo ========================================================
echo  Candidate Screening Agent - Automated Local Setup
echo ========================================================
echo.

cd /d "%~dp0"

:: 1. Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please install Python 3.10+ from https://www.python.org/ and check "Add Python to PATH".
    pause
    exit /b 1
)
python --version

:: 2. Check Node.js & npm
echo.
echo [2/5] Checking Node.js and npm...
npm -v >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js / npm is not installed or not in your system PATH!
    echo Please install Node.js 18+ from https://nodejs.org/.
    pause
    exit /b 1
)
echo Node / npm verified.

:: 3. Setup Backend Virtual Environment
echo.
echo [3/5] Setting up Python virtual environment (backend/venv)...
if not exist "backend\venv" (
    python -m venv backend\venv
)
call backend\venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

:: 4. Install Playwright Browser Binaries
echo.
echo [4/5] Installing Playwright Chromium browser...
python -m playwright install chromium

:: 5. Setup Frontend Dependencies
echo.
echo [5/5] Installing Frontend dependencies (npm install)...
cd frontend
call npm install
cd ..

:: 6. Setup .env file if missing
if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo Created .env from .env.example. Please review your credentials in .env.
    )
)

echo.
echo ========================================================
echo  Setup Completed Successfully!
echo  To start the application, double-click: start_agent.bat
echo ========================================================
pause
