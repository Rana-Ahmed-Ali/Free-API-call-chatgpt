@echo off
title 🚀 PAKI API - AUTO INSTALLER & RUNNER 🚀
color 0A

:: --- 1. Check Python ---
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ and check "Add to PATH" during installation.
    pause
    exit
)

:: --- 2. Check Virtual Environment ---
if not exist "venv" (
    echo [INFO] Creating Virtual Environment...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate

:: --- 3. Install Dependencies ---
echo [INFO] Checking dependencies...
pip install -r requirements.txt >nul 2>&1

:: Check if Playwright browsers need install
if not exist "venv\Lib\site-packages\playwright" (
    echo [INFO] Installing Playwright Browsers...
    playwright install chromium
)

:: --- 4. Check Authentication ---
if not exist "auth.json" (
    echo.
    echo [WARNING] You are not logged in!
    echo Launching Login Script...
    python save_auth.py
    echo.
    echo If login was successful, press any key to continue...
    pause
)

:: --- 5. Launch Everything ---
echo.
echo ======================================================
echo    Starting API + Streamlit + Global Tunnel
echo ======================================================
echo.

:: Start API in background
start "PAKI API SERVER" cmd /k "venv\Scripts\activate && python paki_api.py"

:: Wait for API to warm up
timeout /t 5 >nul

:: Start Streamlit in background
start "STREAMLIT UI" cmd /k "venv\Scripts\activate && streamlit run streamlit_app.py"

:: Start Global Tunnel (Optional)
set /p run_tunnel="Do you want to start the Global URL Tunnel? (y/n): "
if /i "%run_tunnel%"=="y" (
    start "GLOBAL TUNNEL" cmd /k "venv\Scripts\activate && python global_server.py"
)

echo.
echo [SUCCESS] Everything is running!
echo Don't close the popup windows.
pause
