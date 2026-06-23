# ═══════════════════════════════════════════════════════════════════════════
# SamarthX Superset - Local Development Startup Script
# ═══════════════════════════════════════════════════════════════════════════
# This script starts n8n in a separate window and runs Superset locally.
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SamarthX Superset - Local Dev Mode" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# 1. Start n8n in a new background window
Write-Host "[1/3] Launching n8n in a background window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Write-Host 'Starting n8n server on port 5678...' -ForegroundColor Cyan; `$env:NODE_OPTIONS='--max-old-space-size=4096'; n8n start"
Start-Sleep -Seconds 2

# 2. Configure Environment
Write-Host "[2/3] Setting up environment..." -ForegroundColor Yellow
$env:SUPERSET_CONFIG_PATH = "$PWD\superset_config.py"
Write-Host "  ✓ Config Path: $env:SUPERSET_CONFIG_PATH" -ForegroundColor Gray

# 3. Start Superset dev server
Write-Host "[3/3] Starting Superset dev server on http://127.0.0.1:5000 ..." -ForegroundColor Yellow
Write-Host "  Press Ctrl+C to stop the Superset server." -ForegroundColor Gray
Write-Host ""

.\venv_310\Scripts\python.exe run_superset.py run -p 5000 --with-threads --reload
