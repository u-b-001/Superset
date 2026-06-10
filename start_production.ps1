# ═══════════════════════════════════════════════════════════════════════════
# SamarthX Superset - Production Startup Script
# ═══════════════════════════════════════════════════════════════════════════
# This script starts Superset using Gunicorn (production WSGI server)
# ═══════════════════════════════════════════════════════════════════════════

Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SamarthX Superset - Production Mode" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (!(Test-Path ".\.env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure it." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Steps:" -ForegroundColor Cyan
    Write-Host "  1. Copy-Item .env.example .env" -ForegroundColor White
    Write-Host "  2. Edit .env and set SUPERSET_SECRET_KEY and GUEST_TOKEN_JWT_SECRET" -ForegroundColor White
    Write-Host "  3. Generate secrets with: python -c 'import secrets; print(secrets.token_urlsafe(42))'" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Activate virtual environment
Write-Host "[1/5] Activating virtual environment..." -ForegroundColor Yellow
& ".\venv_310\Scripts\Activate.ps1"

# Load environment variables from .env file
Write-Host "[2/5] Loading environment variables..." -ForegroundColor Yellow
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
        Write-Host "  ✓ Loaded $key" -ForegroundColor Gray
    }
}

# Verify required environment variables
Write-Host "[3/5] Verifying configuration..." -ForegroundColor Yellow
$required_vars = @("SUPERSET_SECRET_KEY", "GUEST_TOKEN_JWT_SECRET", "DATABASE_URI")
$missing_vars = @()

foreach ($var in $required_vars) {
    $value = [Environment]::GetEnvironmentVariable($var, "Process")
    if ([string]::IsNullOrEmpty($value) -or $value -like "*CHANGE_ME*") {
        $missing_vars += $var
        Write-Host "  ✗ $var is not set or uses default value!" -ForegroundColor Red
    } else {
        Write-Host "  ✓ $var is configured" -ForegroundColor Green
    }
}

if ($missing_vars.Count -gt 0) {
    Write-Host ""
    Write-Host "ERROR: Required environment variables are missing or not configured:" -ForegroundColor Red
    $missing_vars | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "Please edit the .env file and set these variables." -ForegroundColor Yellow
    exit 1
}

# Set configuration path
$env:SUPERSET_CONFIG_PATH = "$PWD\superset_config.py"
Write-Host "  ✓ Configuration: $env:SUPERSET_CONFIG_PATH" -ForegroundColor Green

# Check if Gunicorn is installed
Write-Host "[4/5] Checking production server..." -ForegroundColor Yellow
$gunicorn_check = python -c "import gunicorn" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Gunicorn not found. Installing..." -ForegroundColor Yellow
    pip install gunicorn
}
Write-Host "  ✓ Gunicorn ready" -ForegroundColor Green

# Start Superset with Gunicorn
Write-Host "[5/5] Starting Superset..." -ForegroundColor Yellow
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Superset is starting on http://0.0.0.0:8088" -ForegroundColor Green
Write-Host "  Mode: PRODUCTION" -ForegroundColor Green
Write-Host "  Workers: 4" -ForegroundColor Green
Write-Host ""
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Start with Gunicorn (production-grade WSGI server)
gunicorn `
    --bind 0.0.0.0:8088 `
    --workers 4 `
    --worker-class gthread `
    --threads 4 `
    --timeout 300 `
    --keep-alive 5 `
    --max-requests 1000 `
    --max-requests-jitter 100 `
    --access-logfile - `
    --error-logfile - `
    --log-level info `
    "superset.app:create_app()"
