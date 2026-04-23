# Anika — install as a Windows service using NSSM (the Non-Sucking Service Manager).
#
# Prereq:
#   1. Download NSSM from https://nssm.cc/download and put nssm.exe on PATH,
#      or in the project root.
#   2. Run this script as Administrator.
#
# Result:
#   A Windows service named "Anika" that starts uvicorn on boot.

$ErrorActionPreference = "Stop"
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
    Write-Error "This script must run as Administrator."
    exit 1
}

Set-Location -Path (Split-Path -Parent $PSScriptRoot)

$nssm = "nssm"
if (-not (Get-Command $nssm -ErrorAction SilentlyContinue)) {
    if (Test-Path ".\nssm.exe") {
        $nssm = (Resolve-Path ".\nssm.exe").Path
    } else {
        Write-Error "nssm not found. Download from https://nssm.cc/ and place nssm.exe in this folder."
        exit 1
    }
}

$serviceName = "Anika"
$python = (Resolve-Path ".\.venv\Scripts\python.exe").Path
$projectDir = (Get-Location).Path

# Remove existing service if present.
& $nssm stop $serviceName confirm 2>$null
& $nssm remove $serviceName confirm 2>$null

Write-Host "Installing service '$serviceName'..."
& $nssm install $serviceName $python "-m" "uvicorn" "app.main:app" "--host" "127.0.0.1" "--port" "8000"
& $nssm set $serviceName AppDirectory $projectDir
& $nssm set $serviceName AppStdout  "$projectDir\data\logs\anika.out.log"
& $nssm set $serviceName AppStderr  "$projectDir\data\logs\anika.err.log"
& $nssm set $serviceName Start SERVICE_AUTO_START
& $nssm set $serviceName DisplayName "Anika — AI email assistant for CA S V Prakasha"
& $nssm set $serviceName Description "Anika: MarketIQX agentic email assistant for Balakrishna & Co."

Write-Host "Starting service..."
& $nssm start $serviceName

Write-Host "Done. Check status with: nssm status $serviceName" -ForegroundColor Green
