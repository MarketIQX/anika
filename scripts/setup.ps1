# Anika — one-time setup
# Runs: venv creation (if missing), pip install, DB init + backfill.

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment (.venv)..."
    python -m venv .venv
}

Write-Host "Upgrading pip..."
& .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip

Write-Host "Installing dependencies from requirements.txt..."
& .\.venv\Scripts\python.exe -m pip install --quiet -r requirements.txt

if (-not (Test-Path ".\.env")) {
    if (Test-Path ".\.env.example") {
        Copy-Item ".\.env.example" ".\.env"
        Write-Warning ".env did not exist; copied from .env.example. Edit it with real keys before running start.ps1."
    } else {
        Write-Warning "No .env file. Create one with OPENAI_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET."
    }
}

Write-Host "Initializing database (anika.db)..."
& .\.venv\Scripts\python.exe -c "from app.db import init_db; init_db(); print('DB ready.')"

Write-Host "Seeding firm_knowledge, rules, and agent prompts..."
& .\.venv\Scripts\python.exe -m app.jobs.backfill_memory

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next: .\scripts\start.ps1"
