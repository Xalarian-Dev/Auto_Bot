@echo off
cd /d "%~dp0"

:: -------------------------------------------------------
:: First-run setup: create venv and install requirements
:: -------------------------------------------------------

if not exist ".venv\Scripts\python.exe" (
    echo [Auto_Bot] No virtual environment found. Creating one...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment. Make sure Python is installed.
        pause
        exit /b 1
    )
    echo [Auto_Bot] Installing dependencies...
    .venv\Scripts\pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [Auto_Bot] Setup complete.
)

:: -------------------------------------------------------
:: Check for candidate profile
:: -------------------------------------------------------

if not exist "assets\candidate.yaml" (
    echo [Auto_Bot] No candidate profile found.
    echo.
    echo            Opening the template in Notepad...
    echo            Fill in your details, then save the file as:
    echo               assets\candidate.yaml
    echo            ^(File ^> Save As... in Notepad^)
    echo.
    start /wait notepad "assets\candidate.yaml.example"
    echo Press any key once you have saved assets\candidate.yaml to continue.
    pause
    if not exist "assets\candidate.yaml" (
        echo [ERROR] assets\candidate.yaml still not found. Please save the file and relaunch.
        pause
        exit /b 1
    )
)

:: -------------------------------------------------------
:: Check for .env
:: -------------------------------------------------------

if not exist ".env" (
    echo [Auto_Bot] No .env file found.
    echo            Copy .env.example to .env and add your API keys.
    pause
    exit /b 1
)

:: -------------------------------------------------------
:: Launch dashboard
:: -------------------------------------------------------

echo [Auto_Bot] Starting dashboard...
.venv\Scripts\streamlit run app.py
