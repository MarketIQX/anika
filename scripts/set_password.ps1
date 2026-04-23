# scripts/set_password.ps1 — change a user's password.
#
# Usage (interactive prompt for password, never echoed):
#   .\scripts\set_password.ps1 -Email aks@marketiqx.com
#
# Usage (inline, NOT recommended — ends up in PSReadLine history):
#   .\scripts\set_password.ps1 -Email aks@marketiqx.com -Password "newpass"
#
# NOTE: The Python implementation lives in scripts/_set_password_impl.py
# because PowerShell's native-exe argument handling strips double-quote
# characters out of inline `-c` code, causing a Python SyntaxError.

param(
    [Parameter(Mandatory = $true)]
    [string]$Email,

    [Parameter(Mandatory = $false)]
    [string]$Password
)

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Virtual environment not found. Run .\scripts\setup.ps1 first."
    exit 1
}

if (-not $Password) {
    $sec = Read-Host -Prompt "New password for $Email" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    try {
        $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

if (-not $Password) {
    Write-Error "Empty password."
    exit 1
}

# Pass password via stdin so it never appears in process args.
$py = ".\.venv\Scripts\python.exe"
$Password | & $py ".\scripts\_set_password_impl.py" $Email
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
