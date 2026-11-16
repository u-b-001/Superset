# ═══════════════════════════════════════════════════════════════════════════
# SamarthX - Dedicated n8n Server Launcher
# ═══════════════════════════════════════════════════════════════════════════

$host.UI.RawUI.WindowTitle = "SamarthX - n8n Workflow Server (Port 5678)"

Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "  SamarthX - n8n Workflow Server Launcher" -ForegroundColor Green
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host ""

$port = 5678
$healthUrl = "http://127.0.0.1:$port/"

# Check if n8n is already responding
try {
    $resp = Invoke-WebRequest -Uri $healthUrl -Method Head -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    Write-Host "[OK] n8n server is ALREADY RUNNING and active at: http://localhost:$port" -ForegroundColor Green
    Write-Host "     Editor UI: http://localhost:$port" -ForegroundColor Cyan
    Write-Host "     Webhook  : http://localhost:$port/webhook/ai-chat" -ForegroundColor Cyan
    exit 0
} catch {
    # Not running yet, proceed with startup
}

# Optimized environment variables for fast offline/online startup
$env:NODE_OPTIONS = "--max-old-space-size=4096"
$env:N8N_HOST = "0.0.0.0"
$env:N8N_PORT = "$port"
$env:N8N_DIAGNOSTICS_ENABLED = "false"
$env:N8N_VERSION_NOTIFICATIONS_ENABLED = "false"
$env:N8N_TEMPLATES_ENABLED = "false"
$env:N8N_HIRING_BANNER_ENABLED = "false"
$env:N8N_DISABLE_PRODUCTION_MAIN_PROCESS_WARN = "true"

# Locate n8n executable
$nodeExe = "C:\Program Files\nodejs\node.exe"
$npmBin = Join-Path $env:APPDATA "npm\node_modules\n8n\bin\n8n"

if ((Test-Path $nodeExe) -and (Test-Path $npmBin)) {
    Write-Host "[*] Starting n8n via Node runtime..." -ForegroundColor Yellow
    & $nodeExe $npmBin start
} else {
    Write-Host "[*] Starting n8n from PATH..." -ForegroundColor Yellow
    n8n start
}
