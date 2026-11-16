
# ═══════════════════════════════════════════════════════════════════════════
# SamarthX - Live Query & Security Audit Terminal
# ═══════════════════════════════════════════════════════════════════════════
# Opens a dedicated terminal to view live query validation, database routing,
# and dashboard KPI synchronization in real time.
# ═══════════════════════════════════════════════════════════════════════════

$host.UI.RawUI.WindowTitle = "SamarthX - Live Query & Security Audit Terminal"

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SamarthX - Live Query & Security Audit Terminal" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check if a background process is holding port 5001
$conns = Get-NetTCPConnection -LocalPort 5001 -ErrorAction SilentlyContinue
if ($conns) {
    Write-Host "[!] Reallocating Port 5001 from background process to this visible window..." -ForegroundColor Yellow
    $conns | ForEach-Object { 
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue 
    }
    Start-Sleep -Milliseconds 900
}

Write-Host "[OK] Starting Live Query Bridge in this terminal..." -ForegroundColor Green
Write-Host "     All questions asked in Superset chat will stream here in real time." -ForegroundColor Gray
Write-Host ""

while ($true) {
    .\venv_310\Scripts\python.exe ai_integration\websocket_server.py
    Write-Host "`n[!] Server process terminated. Reloading in 2 seconds... (Press Ctrl+C to stop)" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}
