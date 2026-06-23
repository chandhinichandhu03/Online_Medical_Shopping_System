# MediCart Store Runner (PowerShell)
Write-Host "Starting MediCart Store Setup..." -ForegroundColor Cyan

# 1. Check for Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in your PATH. Please install it from python.org."
    Pause
    exit
}

# 2. Check for manage.py
if (!(Test-Path "manage.py")) {
    Write-Error "manage.py not found! Please run this script from the project root folder."
    Pause
    exit
}

# 3. Create Virtual Environment
if (!(Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# 4. Activate and Install
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& .\.venv\Scripts\pip.exe install -r requirements.txt

# 5. Database Migrations
Write-Host "Applying migrations..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe manage.py migrate

# 6. Start Server
Write-Host "Starting server at http://127.0.0.1:8000" -ForegroundColor Green
Start-Process "http://127.0.0.1:8000"
& .\.venv\Scripts\python.exe manage.py runserver
