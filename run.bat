@echo off
cd /d %~dp0
if not exist venv\Scripts\activate.bat (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create venv. Make sure Python 3.10+ is installed and on PATH.
        exit /b 1
    )
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install requirements.
        exit /b 1
    )
) else (
    call venv\Scripts\activate.bat
)
python -m reeview
