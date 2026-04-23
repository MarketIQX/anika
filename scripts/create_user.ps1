# scripts/create_user.ps1 — add a new dashboard user.
#
# Usage:
#   .\scripts\create_user.ps1 -Email new.user@example.com -Role user
# Password is prompted for (not echoed).
#
# NOTE: The Python implementation lives in scripts/_create_user_impl.py —
# see the comment in set_password.ps1 for why.

param(
    [Parameter(Mandatory = $true)]
    [string]$Email,

    [Parameter(Mandatory = $true)]
    [ValidateSet("admin","user")]
    [string]$Role,

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
    $sec = Read-Host -Prompt "Password for $Email" -AsSecureString
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

$py = ".\.venv\Scripts\python.exe"
$Password | & $py ".\scripts\_create_user_impl.py" $Email $Role
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
