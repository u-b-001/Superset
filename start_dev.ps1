# ═══════════════════════════════════════════════════════════════════════════
# SamarthX Superset - Local Development Startup Script
# ═══════════════════════════════════════════════════════════════════════════
# Starts and verifies n8n & WebSocket services, then runs Superset.
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SamarthX Superset - Full Development Environment" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# 1. Set environment
$env:SUPERSET_CONFIG_PATH = "$PWD\superset_config.py"
Write-Host "[1/3] Environment configured: SUPERSET_CONFIG_PATH = $env:SUPERSET_CONFIG_PATH" -ForegroundColor Gray

# 2. Start and verify background AI services via service_manager
Write-Host "[2/3] Checking & warming up AI integration services..." -ForegroundColor Yellow
.\venv_310\Scripts\python.exe -m ai_integration.service_manager start

# 3. Start Superset dev server
Write-Host "[3/3] Starting Superset on http://127.0.0.1:5000 ..." -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop the Superset server." -ForegroundColor Gray
Write-Host ""

.\venv_310\Scripts\python.exe run_superset.py run -p 5000 --with-threads --reload


