# SamarthX Superset - Production Deployment Guide

Complete step-by-step guide to deploy Superset on Linux server `172.16.0.106` with domain `bot.demosamarthx.du.ac.in`.

---

## Deployment Workflow Overview

```
┌─────────────────────────┐         ┌──────────────────────────┐
│   GitHub Repository     │  pull   │   Production Server      │
│ Adarshvis/Superset.git  │ ──────▶ │      172.16.0.106        │
│                         │         │      /opt/superset       │
│  ✓ superset_config.py   │         │                          │
│  ✓ requirement.txt      │         │  Files from GitHub       │
│  ✓ static/              │         │  + .env (manual)         │
│  ✓ deploy_to_server.sh  │         │  + DB backup (scp)       │
│  ✗ .env (gitignored)    │         │  + venv (created)        │
│  ✗ *.sql (gitignored)   │         │                          │
└─────────────────────────┘         └──────────────────────────┘
                                              │
                                              ▼
                                     ┌────────────────┐
                                     │ Nginx + SSL    │
                                     │     ↓          │
                                     │ Gunicorn:8088  │
                                     │     ↓          │
                                     │ PostgreSQL     │
                                     └────────────────┘
                                              │
                                              ▼
                                  https://bot.demosamarthx.du.ac.in
```

**Files to transfer manually (NOT via git):**
- `.env` - copy contents from local `.env` (contains real secrets)
- `superset_backup_YYYYMMDD_HHMMSS.sql` - upload via SCP

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Server Initial Setup](#2-server-initial-setup)
3. [Install PostgreSQL](#3-install-postgresql)
4. [Install Python 3.10](#4-install-python-310)
5. [Clone Repository](#5-clone-repository)
6. [Setup Virtual Environment](#6-setup-virtual-environment)
7. [Restore Database](#7-restore-database)
8. [Configure Environment Variables](#8-configure-environment-variables)
9. [Verify Application Starts](#9-verify-application-starts)
10. [Setup Gunicorn Production Server](#10-setup-gunicorn-production-server)
11. [Setup Systemd Service](#11-setup-systemd-service)
12. [Setup Nginx Reverse Proxy](#12-setup-nginx-reverse-proxy)
13. [Setup SSL with Certbot](#13-setup-ssl-with-certbot)
14. [Final Verification](#14-final-verification)
15. [Backup Strategy](#15-backup-strategy)
16. [Troubleshooting](#16-troubleshooting)
17. [Quick Deploy - All Commands](#17-quick-deploy---all-commands)

---

## 1. Prerequisites

**Server Requirements:**
- Linux Ubuntu 22.04 or 24.04 LTS
- Minimum 4GB RAM, 2 CPU cores, 20GB disk
- Root or sudo access
- Network access to `172.16.0.119` (data source DB)

**You should have:**
- SSH access to `172.16.0.106`
- The latest `superset_backup_*.sql` file from your local machine
- The `.env` file values (SECRET_KEY, DATABASE_URI, etc.)
- Domain `bot.demosamarthx.du.ac.in` pointing to `172.16.0.106`

---

## 2. Server Initial Setup

```bash
# SSH into the server
ssh user@172.16.0.106

# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y build-essential libssl-dev libffi-dev \
    libsasl2-dev libldap2-dev libpq-dev pkg-config \
    git curl wget unzip nginx
```

---

## 3. Install PostgreSQL

> **Note:** If PostgreSQL 18.2 is already installed on the server, skip the install commands and only run the database/user creation.

```bash
# Check if PostgreSQL is already installed
psql --version
# If output shows "psql (PostgreSQL) 18.x" - SKIP install, go directly to creating user/database below

# If NOT installed, install PostgreSQL 16+
sudo apt install -y postgresql postgresql-contrib

# Start and enable
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Verify it's running
sudo systemctl status postgresql

# Create Superset database and user (run this regardless of whether you installed or it was pre-installed)
sudo -u postgres psql <<EOF
CREATE USER superset_user WITH PASSWORD 'password';
CREATE DATABASE superset OWNER superset_user;
GRANT ALL PRIVILEGES ON DATABASE superset TO superset_user;
\q
EOF

# Test connection
PGPASSWORD=password psql -h localhost -U superset_user -d superset -c "SELECT version();"
```

> **Note:** Keep the password as `password` to match your existing encrypted database connections. If you change it, update `DATABASE_URI` in `.env`.

---

## 4. Install Python 3.10

```bash
# Add deadsnakes PPA for Python 3.10
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.10 and tools
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3-pip

# Verify
python3.10 --version
```

---

## 5. Clone Repository

```bash
# Create app directory
sudo mkdir -p /opt/superset
sudo chown $USER:$USER /opt/superset

# Clone from GitHub
cd /opt
git clone https://github.com/Adarshvis/Superset.git superset
cd /opt/superset
```

> **Note:** The repository contains code and configuration template only. Two files are NOT in the repo (gitignored) and must be set up manually:
> - `.env` (secrets) - create in step 8
> - `superset_backup_*.sql` (database) - upload via SCP in step 7

---

## 6. Setup Virtual Environment

```bash
cd /opt/superset

# Create virtual environment
python3.10 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install dependencies
pip install -r requirement.txt

# Verify Superset is installed
superset --version

# Copy custom logos/favicon to Superset's static folder
# (Required for branding to work - paths in superset_config.py reference these)
cp /opt/superset/static/assets/samarthx_logo.png \
   /opt/superset/venv/lib/python3.10/site-packages/superset/static/assets/images/

cp /opt/superset/static/assets/SXfavicon.svg \
   /opt/superset/venv/lib/python3.10/site-packages/superset/static/assets/images/
```

---

## 7. Restore Database

> **CRITICAL:** This step has TWO parts. Part A runs on your LOCAL machine, Part B runs on the SERVER.

### Part A: Upload backup file (run on YOUR LOCAL Windows PowerShell)

Open a NEW PowerShell terminal on your local machine (not on the server):

```powershell
scp "C:\Users\Admin\Downloads\superset 2\superset 2\superset\superset_backup_PRODUCTION_READY_20260610_145012.sql" user@172.16.0.106:/tmp/
```

Replace `user` with your actual SSH username. Enter password when prompted.

Verify the file uploaded - on the server (in your SSH session) run:

```bash
ls -lh /tmp/superset_backup_*.sql
# Should show the file with size around 8-9 MB
```

### Part B: Restore the backup (run on the SERVER)

```bash
# Restore from backup
PGPASSWORD=password psql -h localhost -U superset_user -d superset -f /tmp/superset_backup_PRODUCTION_READY_20260610_145012.sql

# Verify
PGPASSWORD=password psql -h localhost -U superset_user -d superset -c "SELECT COUNT(*) FROM dashboards;"
PGPASSWORD=password psql -h localhost -U superset_user -d superset -c "SELECT COUNT(*) FROM slices;"
```

Expected output:
- Dashboards count: 2
- Charts (slices) count: 17

> **CRITICAL:** Do NOT run `superset db upgrade` or `superset init` after restoring. The backup already has the correct schema.

---

## 8. Configure Environment Variables

Create the `.env` file with the SAME values as your local development:

```bash
nano /opt/superset/.env
```

Paste this content:

```env
# Environment mode
SUPERSET_ENV=production

# Embedded portal origin
EMBEDDED_PORTAL_ORIGIN=https://ga.samarthx.du.ac.in

# Flask secret key (MUST match the key used to encrypt DB passwords)
SUPERSET_SECRET_KEY=xLR4BWH/02pWs+Pud3Vw777m7XdYdatiyE+EVIKM6kYEKIBrVVMF4Oxo

# Guest token JWT secret
GUEST_TOKEN_JWT_SECRET=your-guest-token-secret-change-me

# Database connection
DATABASE_URI=postgresql+psycopg2://superset_user:password@localhost:5432/superset
```

Save and exit (Ctrl+X, Y, Enter).

```bash
# Restrict permissions (only owner can read)
chmod 600 /opt/superset/.env
```

---

## 9. Verify Application Starts

```bash
cd /opt/superset
source venv/bin/activate

# Load environment variables and start dev server
export $(grep -v '^#' .env | xargs)
export SUPERSET_CONFIG_PATH=/opt/superset/superset_config.py

# Start Superset (will run on port 8088)
superset run -p 8088 --host 0.0.0.0
```

Open another terminal and test:

```bash
curl http://localhost:8088/health
# Should return: OK
```

If it works, stop the server (Ctrl+C) and proceed to gunicorn setup.

---

## 10. Setup Gunicorn Production Server

```bash
cd /opt/superset
source venv/bin/activate

# Install gunicorn (already in requirement.txt)
pip install gunicorn

# Test gunicorn manually
export $(grep -v '^#' .env | xargs)
export SUPERSET_CONFIG_PATH=/opt/superset/superset_config.py

gunicorn \
  --bind 127.0.0.1:8088 \
  --workers 4 \
  --worker-class gthread \
  --threads 4 \
  --timeout 300 \
  "superset.app:create_app()"
```

If it starts cleanly, stop with Ctrl+C and proceed to systemd.

---

## 11. Setup Systemd Service

Create the service file:

```bash
sudo nano /etc/systemd/system/superset.service
```

Paste:

```ini
[Unit]
Description=SamarthX Superset Service
After=network.target postgresql.service
Requires=postgresql.service

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
    --workers 4 \
    --worker-class gthread \
    --threads 4 \
    --timeout 300 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile /opt/superset/logs/access.log \
    --error-logfile /opt/superset/logs/error.log \
    --log-level info \
    "superset.app:create_app()"

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

> **Replace `User=ubuntu` and `Group=ubuntu`** with your actual server username.

```bash
# Create logs directory
mkdir -p /opt/superset/logs

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable superset
sudo systemctl start superset

# Check status
sudo systemctl status superset

# View logs
sudo journalctl -u superset -f
# OR
tail -f /opt/superset/logs/error.log
```

---

## 12. Setup Nginx Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/superset
```

Paste:

```nginx
# HTTP - redirect to HTTPS
server {
    listen 80;
    server_name bot.demosamarthx.du.ac.in;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name bot.demosamarthx.du.ac.in;

    # SSL certs (configured by certbot in next step)
    ssl_certificate /etc/letsencrypt/live/bot.demosamarthx.du.ac.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.demosamarthx.du.ac.in/privkey.pem;
    
    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Logs
    access_log /var/log/nginx/superset-access.log;
    error_log /var/log/nginx/superset-error.log;

    # Increase upload limits
    client_max_body_size 100M;

    # Proxy timeouts (for long-running queries)
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # Static files (serve directly from nginx for performance)
    location /static/ {
        alias /opt/superset/venv/lib/python3.10/site-packages/superset/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # All other requests go to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (for live features)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site:

```bash
# Create symlink to enable site
sudo ln -s /etc/nginx/sites-available/superset /etc/nginx/sites-enabled/

# Remove default site if it exists
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx config (should show: syntax is ok)
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## 13. Setup SSL with Certbot

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate (will auto-configure nginx)
sudo certbot --nginx -d bot.demosamarthx.du.ac.in

# Test auto-renewal
sudo certbot renew --dry-run
```

Certbot adds a cron job for auto-renewal. Verify:

```bash
sudo systemctl status certbot.timer
```

---

## 14. Final Verification

```bash
# Check all services are running
sudo systemctl status superset
sudo systemctl status nginx
sudo systemctl status postgresql

# Check Superset health
curl http://127.0.0.1:8088/health

# Check public domain (from any machine)
curl https://bot.demosamarthx.du.ac.in/health
```

**Open in browser:** https://bot.demosamarthx.du.ac.in

Login with your admin credentials. Verify:
- ✅ Dashboards load
- ✅ Charts render with data
- ✅ Database connections work
- ✅ Embedding tokens work

---

## 15. Backup Strategy

Setup automated daily backups:

```bash
# Create backup script
sudo nano /opt/superset/backup.sh
```

Paste:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/superset"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=14

mkdir -p $BACKUP_DIR

# Dump database
PGPASSWORD=password pg_dump -h localhost -U superset_user -d superset \
    -f $BACKUP_DIR/superset_backup_$TIMESTAMP.sql

# Compress
gzip $BACKUP_DIR/superset_backup_$TIMESTAMP.sql

# Delete old backups
find $BACKUP_DIR -name "superset_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: superset_backup_$TIMESTAMP.sql.gz"
```

```bash
# Make executable
sudo chmod +x /opt/superset/backup.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
```

Add this line:

```cron
0 2 * * * /opt/superset/backup.sh >> /var/log/superset_backup.log 2>&1
```

---

## 16. Troubleshooting

### Service won't start
```bash
sudo journalctl -u superset -n 100 --no-pager
tail -100 /opt/superset/logs/error.log
```

### "Invalid decryption key" error
The `SUPERSET_SECRET_KEY` in `.env` doesn't match the key used to encrypt the database. Verify it matches your local key exactly:
```
xLR4BWH/02pWs+Pud3Vw777m7XdYdatiyE+EVIKM6kYEKIBrVVMF4Oxo
```

### Charts show "DB engine error"
Database connection passwords couldn't be decrypted. The DB connection password (`Zup1!whb...`) is encrypted with your `SECRET_KEY`. If keys don't match, they won't decrypt.

### Dashboards exist but charts are missing
Check `dashboard_slices` table has entries:
```sql
PGPASSWORD=password psql -h localhost -U superset_user -d superset \
    -c "SELECT COUNT(*) FROM dashboard_slices;"
```

### Permission errors when editing database connections
Run the view_menu fix:
```sql
INSERT INTO ab_view_menu (id, name) 
SELECT nextval('ab_view_menu_id_seq'), 
       '[' || d.database_name || '].[' || t.table_name || '](id:' || t.id || ')'
FROM tables t JOIN dbs d ON t.database_id = d.id
WHERE NOT EXISTS (
    SELECT 1 FROM ab_view_menu 
    WHERE name = '[' || d.database_name || '].[' || t.table_name || '](id:' || t.id || ')'
);
```

### Common commands
```bash
# Restart Superset
sudo systemctl restart superset

# Restart Nginx
sudo systemctl reload nginx

# Check Superset logs
sudo journalctl -u superset -f

# Manual backup
/opt/superset/backup.sh

# Update from GitHub
cd /opt/superset
git pull
sudo systemctl restart superset
```

---

## Critical Rules - DO NOT VIOLATE

1. **NEVER change `SUPERSET_SECRET_KEY`** - it's used to encrypt database passwords
2. **NEVER run `superset db upgrade`** after restoring a backup with same Superset version
3. **NEVER run `superset init`** after restoring a backup - resets permissions
4. **ALWAYS take a backup** before any database operation
5. **NEVER commit `.env` to git** - it contains secrets
6. **ALWAYS test in a non-prod environment first**

---

## Quick Reference

| Item | Value |
|------|-------|
| Server | 172.16.0.106 |
| Domain | bot.demosamarthx.du.ac.in |
| App directory | /opt/superset |
| Virtual env | /opt/superset/venv |
| Config file | /opt/superset/superset_config.py |
| Env file | /opt/superset/.env |
| Logs | /opt/superset/logs/ |
| Backups | /var/backups/superset/ |
| Service | superset.service |
| Internal port | 8088 |
| Database | postgresql://superset_user@localhost:5432/superset |

---

## Support Contacts

- **Repository:** https://github.com/Adarshvis/Superset.git
- **Data source DB:** 172.16.0.119:5432

---

## 17. Quick Deploy - All Commands

> Copy-paste these commands sequentially. Replace `user` with your SSH username.

### STEP 1: From your LOCAL Windows PowerShell - Upload backup

```powershell
scp "C:\Users\Admin\Downloads\superset 2\superset 2\superset\superset_backup_PRODUCTION_READY_20260610_145012.sql" user@172.16.0.106:/tmp/
```

### STEP 2: SSH into the server

```powershell
ssh user@172.16.0.106
```

### STEP 3: On the server - Run all commands below in order

```bash
# Verify backup file is uploaded
ls -lh /tmp/superset_backup_*.sql

# System update
sudo apt update && sudo apt upgrade -y

# Install dependencies (Nginx + build tools + git)
sudo apt install -y build-essential libssl-dev libffi-dev libsasl2-dev libldap2-dev libpq-dev pkg-config git curl wget unzip nginx

# Verify PostgreSQL is installed (should show 18.x)
psql --version

# Start PostgreSQL if not running
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create Superset database and user
sudo -u postgres psql -c "CREATE USER superset_user WITH PASSWORD 'password';"
sudo -u postgres psql -c "CREATE DATABASE superset OWNER superset_user;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE superset TO superset_user;"

# Install Python 3.10
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3-pip

# Clone repository from GitHub
sudo mkdir -p /opt/superset
sudo chown $USER:$USER /opt/superset
cd /opt
git clone https://github.com/Adarshvis/Superset.git superset
cd /opt/superset

# Setup virtual environment and install dependencies
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirement.txt

# Copy custom logos to Superset's static folder (REQUIRED for branding)
cp /opt/superset/static/assets/samarthx_logo.png /opt/superset/venv/lib/python3.10/site-packages/superset/static/assets/images/
cp /opt/superset/static/assets/SXfavicon.svg /opt/superset/venv/lib/python3.10/site-packages/superset/static/assets/images/

# Restore database from backup
PGPASSWORD=password psql -h localhost -U superset_user -d superset -f /tmp/superset_backup_PRODUCTION_READY_20260610_145012.sql

# Verify restore worked
PGPASSWORD=password psql -h localhost -U superset_user -d superset -c "SELECT COUNT(*) FROM dashboards;"

# Create .env file
cat > /opt/superset/.env <<'EOF'
SUPERSET_ENV=production
EMBEDDED_PORTAL_ORIGIN=https://ga.samarthx.du.ac.in
SUPERSET_SECRET_KEY=xLR4BWH/02pWs+Pud3Vw777m7XdYdatiyE+EVIKM6kYEKIBrVVMF4Oxo
GUEST_TOKEN_JWT_SECRET=your-guest-token-secret-change-me
DATABASE_URI=postgresql+psycopg2://superset_user:password@localhost:5432/superset
EOF

chmod 600 /opt/superset/.env
mkdir -p /opt/superset/logs

# Create systemd service
sudo tee /etc/systemd/system/superset.service > /dev/null <<EOF
[Unit]
Description=SamarthX Superset Service
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=/opt/superset
EnvironmentFile=/opt/superset/.env
Environment="SUPERSET_CONFIG_PATH=/opt/superset/superset_config.py"
Environment="PATH=/opt/superset/venv/bin"
ExecStart=/opt/superset/venv/bin/gunicorn --bind 127.0.0.1:8088 --workers 4 --worker-class gthread --threads 4 --timeout 300 --keep-alive 5 --max-requests 1000 --max-requests-jitter 100 --access-logfile /opt/superset/logs/access.log --error-logfile /opt/superset/logs/error.log --log-level info "superset.app:create_app()"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start Superset service
sudo systemctl daemon-reload
sudo systemctl enable superset
sudo systemctl start superset
sudo systemctl status superset

# Test internal endpoint
sleep 5
curl http://127.0.0.1:8088/health

# Configure Nginx (HTTP only - SSL added in next step)
sudo tee /etc/nginx/sites-available/superset > /dev/null <<'EOF'
server {
    listen 80;
    server_name bot.demosamarthx.du.ac.in;
    
    client_max_body_size 100M;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
    
    location /static/ {
        alias /opt/superset/venv/lib/python3.10/site-packages/superset/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location / {
        proxy_pass http://127.0.0.1:8088;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Enable site and reload Nginx
sudo ln -sf /etc/nginx/sites-available/superset /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# Install SSL certificate
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d bot.demosamarthx.du.ac.in --non-interactive --agree-tos --email admin@samarthx.du.ac.in

# Final verification
curl http://127.0.0.1:8088/health
curl https://bot.demosamarthx.du.ac.in/health

# Cleanup uploaded backup file
shred -u /tmp/superset_backup_*.sql
```

### STEP 4: Open in browser

```
https://bot.demosamarthx.du.ac.in
```

Login with admin credentials. Verify dashboards and charts load.

---

**Deployment guide version:** 1.1  
**Last updated:** June 2026
