# ═══════════════════════════════════════════════════════════════════════════
# SamarthX AI Services - Background Process Launcher
# ═══════════════════════════════════════════════════════════════════════════
# Runs n8n and WebSocket server permanently in the background.
# Can be executed standalone or placed in Windows Startup.
# ═══════════════════════════════════════════════════════════════════════════

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$pythonExe = Join-Path $scriptDir "venv_310\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python.exe"
}

Write-Host "Ensuring SamarthX AI Services are running..." -ForegroundColor Cyan
& $pythonExe -m ai_integration.service_manager start
Write-Host "Done. Services are verified and running." -ForegroundColor Green
