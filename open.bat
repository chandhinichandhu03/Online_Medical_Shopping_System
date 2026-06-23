@echo off
echo Starting MediCart Store...

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH. Please install Python.
    pause
    exit
):: Check for manage.py
if not exist "manage.py" (
    echo Error: manage.py not found in the current directory!
    echo Please make sure you are running this script from the project root folder.
    pause
    exit
)

:: Create venv if doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

:: Activate venv
call .venv\Scripts\activate

:: Install requirements
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    pause
    exit
)

:: Migrate
echo Applying migrations...
python manage.py migrate
if %errorlevel% neq 0 (
    echo Migration failed.
    pause
    exit
)

:: Open VS Code and Explorer
echo Opening VS Code and Folder...
call code .
start .

:: Open Browser
echo Opening website...
timeout /t 5 >nul
start http://127.0.0.1:curl -sSL https://install.python-poetry.org | python3 -8000

:: Run Server
echo Starting server...
python manage.py runserver
pause
