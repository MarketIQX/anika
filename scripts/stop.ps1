# Anika — stop any running anika uvicorn process and cloudflared tunnel.

$ErrorActionPreference = "SilentlyContinue"

$stopped = 0
Get-Process -Name "python","python.exe" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $cmd = (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
    } catch { $cmd = "" }
    if ($cmd -and $cmd -match "app\.main:app") {
        Write-Host "Stopping Anika PID $($_.Id)"
        Stop-Process -Id $_.Id -Force
        $stopped += 1
    }
}
Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "Stopping cloudflared PID $($_.Id)"
    Stop-Process -Id $_.Id -Force
    $stopped += 1
}
if ($stopped -eq 0) {
    Write-Host "No Anika process was running."
} else {
    Write-Host "$stopped process(es) stopped." -ForegroundColor Green
}
