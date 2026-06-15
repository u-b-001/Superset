# Production Troubleshooting Guide

Solutions for SamarthX Superset production issues on `172.16.0.106` / `bot.demosamarthx.du.ac.in`.

---

## Issues Covered

1. [CSS Not Loading / UI Broken](#issue-1-css-not-loading)
2. [Application Crashes / Server Down](#issue-2-application-crashes--server-down)
3. [Quick Health Check](#quick-health-check)

---

# ISSUE 1: CSS Not Loading

## Symptoms
- Page loads but looks unstyled (no fonts, broken layout, plain HTML)
- Browser DevTools (F12) → Network tab shows 404 errors for `.css` and `.js` files
- Static images, logos don't appear
- Site works locally but breaks on production

## Why This Happens

Nginx tries to serve static files directly from venv path. If the path is wrong (typically Python version mismatch), all static files return 404.

## Quick Diagnosis

```bash
# 1. Check actual Python version in venv
ls /opt/superset/venv/lib/
# Output: python3.10 (good) OR python3.11 (need to update Nginx)

# 2. Check Nginx error log for 404s
sudo tail -30 /var/log/nginx/superset-error.log

# 3. Test if static file is accessible
curl -I http://127.0.0.1:8088/static/assets/images/samarthx_logo.png
# Should return: HTTP/1.1 200 OK

# 4. Test through Nginx
curl -I https://bot.demosamarthx.du.ac.in/static/assets/images/samarthx_logo.png
# If this is 404 but localhost is 200 = Nginx static path is wrong
```

---

## SOLUTION (Recommended): Remove Nginx Static Block

Let Gunicorn handle all requests including static files. Simplest and most reliable.

```bash
sudo nano /etc/nginx/sites-available/superset
```

**REMOVE** this entire block:

```nginx
location /static/ {
    alias /opt/superset/venv/lib/python3.10/site-packages/superset/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

Save (Ctrl+X, Y, Enter), then:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

**Refresh browser with Ctrl+F5.** CSS should load immediately.

---

## Alternative: Fix Python Path in Nginx

If you want Nginx to keep serving static files (slightly faster):

```bash
# Check Python version
ls /opt/superset/venv/lib/

# Update Nginx config to match
sudo nano /etc/nginx/sites-available/superset
```

Replace the alias line with the correct version:

```nginx
location /static/ {
    alias /opt/superset/venv/lib/python3.XX/site-packages/superset/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

Replace `python3.XX` with actual version (3.10 or 3.11).

```bash
# Make sure Nginx user can read the files
sudo chmod -R 755 /opt/superset/venv/lib/python3.10/site-packages/superset/static/

sudo nginx -t
sudo systemctl reload nginx
```

---

## Logo/Favicon Not Showing

If CSS loads but the SamarthX logo is missing, copy custom branding files:

```bash
cp /opt/superset/static/assets/samarthx_logo.png \
   /opt/superset/venv/lib/python3.10/site-packages/superset/static/assets/images/

cp /opt/superset/static/assets/SXfavicon.svg \
   /opt/superset/venv/lib/python3.10/site-packages/superset/static/assets/images/

sudo systemctl restart superset
```

---

# ISSUE 2: Application Crashes / Server Down

## Symptoms
- 502 Bad Gateway in browser
- `sudo systemctl status superset` shows "failed" or "inactive"
- Service stops responding after some time
- Browser shows "Connection refused"

## First Step: Get Real Error

```bash
# This shows the EXACT error
sudo journalctl -u superset -n 100 --no-pager
```

Look for keywords like:
- `Killed` → memory issue
- `Traceback` → Python error
- `OperationalError` → database issue
- `ImportError` → missing package
- `permission denied` → file permission issue

## Common Crash Causes (Diagnostic)

Run these commands to identify the cause:

```bash
# 1. Service status
sudo systemctl status superset --no-pager

# 2. Disk space
df -h
# Any partition at 100%? → That's it

# 3. Memory (less likely on on-premise)
free -h

# 4. Logs directory exists?
ls -lh /opt/superset/logs/
# If "No such file" → CRITICAL ISSUE

# 5. Environment vars loaded?
sudo systemctl show superset | grep -i secret
# Should show SUPERSET_SECRET_KEY (encrypted)

# 6. .env format correct?
cat /opt/superset/.env
# Each line must be KEY=VALUE (no spaces, no quotes)

# 7. Python version matches
ls /opt/superset/venv/lib/

# 8. Port not in use elsewhere
sudo lsof -i :8088

# 9. Database connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# 10. Superset can actually start
cd /opt/superset
source venv/bin/activate
export $(grep -v '^#' .env | xargs)
export SUPERSET_CONFIG_PATH=/opt/superset/superset_config.py
superset --version
# If this fails, package install is broken
```

---

## SOLUTION 1: Missing Logs Directory (Common Cause)

```bash
mkdir -p /opt/superset/logs
sudo chown -R $USER:$USER /opt/superset/logs
sudo systemctl restart superset
sudo systemctl status superset
```

---

## SOLUTION 2: .env Not Loading

The systemd `EnvironmentFile=` directive expects strict format.

```bash
# View current .env
cat /opt/superset/.env
```

**WRONG format (will fail):**
```env
SUPERSET_SECRET_KEY = "xLR4BWH/..."   # spaces around = and quotes
```

**CORRECT format:**
```env
SUPERSET_SECRET_KEY=xLR4BWH/02pWs+Pud3Vw777m7XdYdatiyE+EVIKM6kYEKIBrVVMF4Oxo
```

Fix:
```bash
# Recreate .env with correct format
cat > /opt/superset/.env <<'EOF'
SUPERSET_ENV=production
EMBEDDED_PORTAL_ORIGIN=https://ga.samarthx.du.ac.in
SUPERSET_SECRET_KEY=xLR4BWH/02pWs+Pud3Vw777m7XdYdatiyE+EVIKM6kYEKIBrVVMF4Oxo
GUEST_TOKEN_JWT_SECRET=your-guest-token-secret-change-me
DATABASE_URI=postgresql+psycopg2://superset_user:password@localhost:5432/superset
EOF

chmod 600 /opt/superset/.env
sudo systemctl restart superset
```

---

## SOLUTION 3: Wrong Python Version Path

If venv has Python 3.11 but systemd references 3.10:

```bash
# Check actual version
ls /opt/superset/venv/lib/

# If it's python3.11, update systemd Environment paths
sudo nano /etc/systemd/system/superset.service
```

The gunicorn binary path should always work via `/opt/superset/venv/bin/gunicorn` regardless of Python version. But the SUPERSET_HOME or any explicit Python path needs updating.

```bash
sudo systemctl daemon-reload
sudo systemctl restart superset
```

---

## SOLUTION 4: Worker Timeout (For Slow Charts)

If long queries crash workers:

```bash
sudo nano /etc/systemd/system/superset.service
```

Increase timeout in ExecStart:

```
--timeout 600  (instead of 300)
--graceful-timeout 60
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart superset
```

---

## SOLUTION 5: Permission Issues

If files were created as root but service runs as different user:

```bash
# Fix ownership
sudo chown -R $USER:$USER /opt/superset

# Fix permissions
sudo chmod 755 /opt/superset
sudo chmod 600 /opt/superset/.env

sudo systemctl restart superset
```

---

## SOLUTION 6: Production-Hardened Systemd Service

Replace the systemd service with this hardened version:

```bash
sudo nano /etc/systemd/system/superset.service
```

```ini
[Unit]
Description=SamarthX Superset Service
After=network.target postgresql.service
Requires=postgresql.service
StartLimitInterval=60
StartLimitBurst=5

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/superset

EnvironmentFile=/opt/superset/.env
Environment="SUPERSET_CONFIG_PATH=/opt/superset/superset_config.py"
Environment="PATH=/opt/superset/venv/bin"

ExecStart=/opt/superset/venv/bin/gunicorn \
    --bind 127.0.0.1:8088 \
    --workers 2 \
    --worker-class gthread \
    --threads 4 \
    --timeout 600 \
    --graceful-timeout 60 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --access-logfile /opt/superset/logs/access.log \
    --error-logfile /opt/superset/logs/error.log \
    --log-level info \
    "superset.app:create_app()"

# Restart on crash
Restart=always
RestartSec=10

# Process management
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

> Replace `User=ubuntu` and `Group=ubuntu` with your actual username.

```bash
mkdir -p /opt/superset/logs
sudo chown -R $USER:$USER /opt/superset/logs

sudo systemctl daemon-reload
sudo systemctl restart superset
sudo systemctl status superset
sudo journalctl -u superset -f
```

---

# Quick Health Check

Run this single command to check everything:

```bash
echo "=== SUPERSET ===" && sudo systemctl is-active superset && \
echo "=== NGINX ===" && sudo systemctl is-active nginx && \
echo "=== POSTGRESQL ===" && sudo systemctl is-active postgresql && \
echo "=== HEALTH ENDPOINT ===" && curl -s http://127.0.0.1:8088/health && \
echo "" && echo "=== PUBLIC URL ===" && curl -sI https://bot.demosamarthx.du.ac.in/health | head -1 && \
echo "=== MEMORY ===" && free -h | head -2 && \
echo "=== DISK ===" && df -h | head -3
```

Expected output (all green):
```
=== SUPERSET ===
active
=== NGINX ===
active
=== POSTGRESQL ===
active
=== HEALTH ENDPOINT ===
OK
=== PUBLIC URL ===
HTTP/1.1 200 OK
=== MEMORY ===
              total        used        free
Mem:           ...G        ...G        ...G
=== DISK ===
Filesystem      Size  Used Avail Use% Mounted on
/dev/...        ...   ...   ...  ..%  /
```

---

## Common Error Reference

| Error in Logs | Likely Cause | Quick Fix |
|---------------|--------------|-----------|
| `Killed` | Out of memory | Reduce workers from 4 to 2 |
| `Invalid decryption key` | SECRET_KEY wrong/missing | Verify `.env` has correct key |
| `OperationalError: could not connect` | PostgreSQL down | `sudo systemctl restart postgresql` |
| `Permission denied: '/opt/superset/logs/access.log'` | Missing logs dir | `mkdir -p /opt/superset/logs` |
| `Worker timeout` | Slow query | Increase `--timeout 600` |
| `ModuleNotFoundError` | Package not installed | `pip install -r requirement.txt` |
| `bind: address already in use` | Port 8088 in use | `sudo lsof -i :8088` and kill |
| `502 Bad Gateway` | Gunicorn not running | `sudo systemctl restart superset` |
| `404 on .css/.js` | Nginx static path wrong | Remove `/static/` block from Nginx |

---

## Emergency Recovery (If All Else Fails)

```bash
# 1. Stop everything
sudo systemctl stop superset

# 2. Verify backups exist
ls -lh /var/backups/superset/

# 3. Restore database from last known-good backup
sudo -u postgres dropdb superset
sudo -u postgres createdb -O superset_user superset
PGPASSWORD=password psql -h localhost -U superset_user -d superset \
    -f /var/backups/superset/superset_backup_LATEST.sql

# 4. Reset permissions
sudo chown -R $USER:$USER /opt/superset

# 5. Reload systemd
sudo systemctl daemon-reload

# 6. Start in order
sudo systemctl start postgresql
sudo systemctl start superset
sudo systemctl reload nginx

# 7. Verify
sudo systemctl status superset
curl http://127.0.0.1:8088/health
```

---

## Critical Rules - DO NOT VIOLATE

1. **NEVER change `SUPERSET_SECRET_KEY`** - breaks encrypted DB passwords
2. **NEVER run `superset db upgrade`** after restoring backup with same version
3. **NEVER run `superset init`** after restoring - resets permissions
4. **ALWAYS take backup** before any database operation
5. **Check `journalctl` FIRST** when troubleshooting

---

## When to Escalate

If after trying all solutions:
- Service still crashes within 5 minutes of starting
- `journalctl` shows no clear error
- Database queries fail consistently

Collect this info:
```bash
sudo journalctl -u superset -n 200 --no-pager > /tmp/superset_debug.log
sudo systemctl status superset --no-pager >> /tmp/superset_debug.log
free -h >> /tmp/superset_debug.log
df -h >> /tmp/superset_debug.log
ls -lh /opt/superset/logs/ >> /tmp/superset_debug.log 2>&1
cat /opt/superset/.env | sed 's/=.*/=***/' >> /tmp/superset_debug.log
```

Then `cat /tmp/superset_debug.log` and share the output.

---

**Server:** 172.16.0.106  
**Domain:** bot.demosamarthx.du.ac.in  
**Local versions:** Superset 6.0.0, Python 3.10.11, PostgreSQL 18.2  
**Last updated:** June 2026
