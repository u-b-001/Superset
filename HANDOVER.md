# SamarthX Superset - Handover Guide

Everything a new team member needs to run this project locally and deploy it.

---

## What This Project Is

A customized Apache Superset (v6.0.0) dashboard application for SamarthX (Goa education data), with:
- Custom SamarthX branding (logo, colors, favicon)
- 2 dashboards, 17 charts (employee + school data)
- An **AI chat assistant** (natural language → SQL) powered by n8n + Google Gemini 2.5 Flash

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Superset (port 5000 local / 8088 prod)             │
│  - Dashboards + Charts                              │
│  - AI chat widget (bottom-right button)             │
└───────────────┬─────────────────────────────────────┘
                │ AI questions
                ▼
┌─────────────────────────────────────────────────────┐
│  n8n (port 5678) - workflow engine                  │
│   Webhook → Gemini (SQL) → Validate → Postgres →    │
│   Gemini (format answer) → Respond                  │
└───────┬──────────────────────────┬──────────────────┘
        │ LLM                       │ data query
        ▼                           ▼
┌──────────────┐         ┌────────────────────────────┐
│  Gemini API  │         │ Data DB 172.16.0.119:5432  │
│  2.5 Flash   │         │ employee_db + org_db       │
└──────────────┘         └────────────────────────────┘

Superset metadata DB: PostgreSQL localhost:5432/superset
```

---

## PART A: What YOU (handing over) must do

### 1. Push code to GitHub

```powershell
cd "path\to\superset"

# Verify what will be committed (should NOT include .env, *.sql, venv_310/)
git status

# Stage everything (gitignore protects secrets/backups/venv)
git add .

# Commit
git commit -m "Superset with AI chat integration - handover"

# Push
git push
```

### 2. Share these SEPARATELY (NOT via GitHub - they contain secrets)

Send your teammate through a secure channel (password manager / encrypted message):

| Item | Value / File |
|------|--------------|
| `.env` file contents | The whole file (SECRET_KEY, DATABASE_URI, etc.) |
| Latest DB backup | `superset_backup_PRODUCTION_READY_*.sql` (the newest one) |
| Data DB password | `dashboard_read_only_user` password for 172.16.0.119 |

> **Why separate:** `.env` and `*.sql` are gitignored on purpose (they hold secrets and data).

---

## PART B: What YOUR TEAMMATE must do (local setup)

### Prerequisites to install
- Python 3.10
- PostgreSQL 18 (or 16+)
- Node.js (for n8n)
- Google Gemini API Key

### Step 1: Clone the repo
```bash
git clone <repo-url> superset
cd superset
```

### Step 2: Create Python virtual environment
```bash
python3.10 -m venv venv_310
# Windows:
.\venv_310\Scripts\activate
# Linux/Mac:
source venv_310/bin/activate

pip install --upgrade pip
pip install -r requirement.txt
```

### Step 3: Create the `.env` file
Create `.env` in the project root with the contents you received separately:
```env
SUPERSET_ENV=development
EMBEDDED_PORTAL_ORIGIN=https://ga.samarthx.du.ac.in
SUPERSET_SECRET_KEY=<from handover>
GUEST_TOKEN_JWT_SECRET=<from handover>
DATABASE_URI=postgresql+psycopg2://superset_user:password@localhost:5432/superset
```

> CRITICAL: SUPERSET_SECRET_KEY must be the EXACT value handed over. It decrypts the database passwords. A different key breaks everything.

### Step 4: Set up local PostgreSQL (Superset metadata DB)
```bash
# Create user + database
psql -U postgres -c "CREATE USER superset_user WITH PASSWORD 'password';"
psql -U postgres -c "CREATE DATABASE superset OWNER superset_user;"

# Restore the backup (file received separately)
psql -U superset_user -d superset -f superset_backup_PRODUCTION_READY_XXXX.sql
```

> DO NOT run `superset db upgrade` or `superset init` after restore - it breaks the restored state.

### Step 5: Apply custom branding (logo + AI chat widget)
The custom templates are in the repo at `custom_templates/`. Copy them into the installed Superset package:

```bash
# Windows
copy custom_templates\tail_js_custom_extra.html venv_310\Lib\site-packages\superset\templates\
copy custom_templates\head_custom_extra.html venv_310\Lib\site-packages\superset\templates\

# Linux/Mac
cp custom_templates/*.html venv_310/lib/python3.10/site-packages/superset/templates/
```

Also copy the logo images:
```bash
# Windows
copy static\assets\samarthx_logo.png venv_310\Lib\site-packages\superset\static\assets\images\
copy static\assets\SXfavicon.svg venv_310\Lib\site-packages\superset\static\assets\images\
```

### Step 6: Start Superset
```bash
$env:SUPERSET_CONFIG_PATH="$PWD\superset_config.py"   # Windows
# export SUPERSET_CONFIG_PATH=$PWD/superset_config.py  # Linux

# If superset is blocked by Windows Application Control or shebang issues:
python run_superset.py run -p 5000 --with-threads --reload

# Otherwise:
# superset run -p 5000 --with-threads --reload
```
Open http://127.0.0.1:5000 - dashboards + logo should appear.

---

## PART C: AI Chat Setup (n8n + Gemini)

The AI chat needs n8n and a Google Gemini API Key. Setup details are in `ai_integration/`.

### Step 1: Get a Gemini API Key
Create an API key in Google AI Studio and configure it in the HTTP Request nodes inside n8n.

### Step 2: Install + start n8n
```bash
npm install -g n8n
n8n start
```
Open http://localhost:5678, complete owner account setup.

### Step 3: Import the n8n workflow
```bash
n8n import:workflow --input=ai_integration/n8n_workflow.json
```

### Step 4: Create the two PostgreSQL credentials in n8n UI
Open http://localhost:5678 → Credentials → Add → Postgres. Create BOTH:

| Credential Name | Database | Host | User | Password | Port |
|-----------------|----------|------|------|----------|------|
| `SamarthX Data DB` | employee_db | 172.16.0.119 | dashboard_read_only_user | (received) | 5432 |
| `SamarthX Org DB` | org_db | 172.16.0.119 | dashboard_read_only_user | (received) | 5432 |

> Credential names must match EXACTLY (the workflow references them by name).

### Step 5: Link credentials + activate
1. Open the "SamarthX AI Chat" workflow
2. Click **Query Employee DB** node → select `SamarthX Data DB`
3. Click **Query Org DB** node → select `SamarthX Org DB`
4. Toggle **Active** (top-right) to ON
5. Save

### Step 6: Test
```bash
curl -X POST http://localhost:5678/webhook/ai-chat \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"How many teachers are in Goa?\"}"
```
Expected: `{"answer": "There are 14,376 teachers in Goa."}`

> Requires network access to 172.16.0.119 (VPN if off-site).

---

## Repository Structure

```
superset/
├── superset_config.py          # Main config (reads secrets from .env)
├── requirement.txt             # Python dependencies (Superset 6.0.0)
├── .env.example                # Template (real .env is gitignored)
├── .gitignore
├── static/assets/              # Logo + favicon source files
├── custom_templates/           # Logo + AI chat widget (copy to venv)
│   ├── tail_js_custom_extra.html
│   └── head_custom_extra.html
├── ai_integration/             # AI chat feature
│   ├── README.md
│   ├── schema_prompt.md        # DB schema + AI prompt
│   ├── n8n_workflow.json       # Importable n8n workflow
│   ├── n8n_workflow_guide.md
│   └── chat_widget.html        # Reference copy of the widget
├── DEPLOYMENT_GUIDE.md         # Production deployment (server 172.16.0.106)
├── PRODUCTION_TROUBLESHOOTING.md
└── HANDOVER.md                 # This file
```

---

## NOT in the repo (received separately)
- `.env` - real secrets
- `superset_backup_*.sql` - database dump
- `venv_310/` - rebuilt via `pip install -r requirement.txt`
- Data DB password

---

## Critical Rules (DO NOT VIOLATE)

1. **NEVER change `SUPERSET_SECRET_KEY`** - it encrypts DB connection passwords
2. **NEVER run `superset db upgrade` or `superset init`** after restoring a backup
3. **ALWAYS back up** (`pg_dump`) before any database change
4. Superset version must stay **6.0.0** (matches encrypted data)
5. Keep `.env` out of git

---

## Quick Reference

| Item | Value |
|------|-------|
| Superset version | 6.0.0 |
| Python | 3.10 |
| PostgreSQL | 18 |
| AI model | gemini-2.5-flash |
| Local Superset | http://127.0.0.1:5000 |
| n8n | http://localhost:5678 |
| Gemini API | https://generativelanguage.googleapis.com |
| Data DB | 172.16.0.119:5432 (employee_db, org_db) |
| Production server | 172.16.0.106 (bot.demosamarthx.du.ac.in) |

---

## Key Documentation
- **Production deploy:** `DEPLOYMENT_GUIDE.md`
- **Troubleshooting:** `PRODUCTION_TROUBLESHOOTING.md`
- **AI chat details:** `ai_integration/README.md`
