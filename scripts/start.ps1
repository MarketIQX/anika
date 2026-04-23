# Anika — start the FastAPI server (and optionally the Cloudflare Tunnel).
#
# Usage:
#   .\scripts\start.ps1          # server only, http://localhost:8000
#   .\scripts\start.ps1 -Tunnel  # also start Cloudflare Tunnel (cloudflared must be present)

param(
    [switch]$Tunnel
)

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Virtual environment not found. Run .\scripts\setup.ps1 first."
    exit 1
}

# Load .env into the current PowerShell session so uvicorn inherits the vars.
if (Test-Path ".\.env") {
    Get-Content .\.env | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]*)=(.*)$") {
            [Environment]::SetEnvironmentVariable($Matches[1].Trim(), $Matches[2].Trim(), "Process")
        }
    }
}

$AnikaHost = if ($env:ANIKA_HOST) { $env:ANIKA_HOST } else { "127.0.0.1" }
$AnikaPort = if ($env:ANIKA_PORT) { $env:ANIKA_PORT } else { "8000" }

if ($Tunnel) {
    $cfd = ".\cloudflared.exe"
    if (-not (Test-Path $cfd)) {
        Write-Warning "cloudflared.exe not found in project root. Skipping tunnel. See README for install."
    } else {
        Write-Host "Starting Cloudflare Tunnel (background)..."
        $tunnelName = if ($env:CLOUDFLARE_TUNNEL_NAME) { $env:CLOUDFLARE_TUNNEL_NAME } else { "anika" }
        Start-Process -FilePath $cfd `
            -ArgumentList "tunnel","--url","http://$AnikaHost`:$AnikaPort","run",$tunnelName `
            -WindowStyle Hidden
    }
}

Write-Host "Anika listening on http://$AnikaHost`:$AnikaPort" -ForegroundColor Green
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host $AnikaHost --port $AnikaPort
