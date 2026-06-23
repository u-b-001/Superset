# SamarthX Superset - Local Setup Guide

Follow these steps in order to get the project running on your machine.

> **Before you start, get these from the person handing over (NOT in GitHub):**
> 1. The `.env` file contents
> 2. The database backup file: `superset_backup_PRODUCTION_READY_XXXX.sql`
> 3. The data DB password (for `dashboard_read_only_user`)

---

## 1. Install Prerequisites

Install these on your machine:

| Software | Version | Download |
|----------|---------|----------|
| Python | 3.10 | https://www.python.org/downloads/release/python-31011/ |
| PostgreSQL | 18 (or 16+) | https://www.postgresql.org/download/ |
| Node.js | LTS | https://nodejs.org/ (needed for n8n) |
| Google Gemini | API key | https://aistudio.google.com/ (for AI chat) |
| Git | latest | https://git-scm.com/ |

Verify installs:
```powershell
python --version        # should be 3.10.x
psql --version          # should be 18.x
node --version
git --version
```

---

## 2. Clone the Repository

```powershell
git clone <REPO_URL> superset
cd superset
```

---

## 3. Python Virtual Environment

```powershell
# Create venv
python -m venv venv_310

# Activate (Windows PowerShell)


# Upgrade pip and install dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirement.txt
```

This installs Superset 6.0.0 and all dependencies (takes a few minutes).

Verify:
```powershell
pip show apache-superset    # Version should be 6.0.0
```

---

## 4. Create the `.env` File

Create a file named `.env` in the project root. Paste the contents you received during handover. It looks like this:

```env
SUPERSET_ENV=development
EMBEDDED_PORTAL_ORIGIN=https://ga.samarthx.du.ac.in
SUPERSET_SECRET_KEY=<exact value from handover>
GUEST_TOKEN_JWT_SECRET=<exact value from handover>
DATABASE_URI=postgresql+psycopg2://superset_user:password@localhost:5432/superset
```

> **CRITICAL:** `SUPERSET_SECRET_KEY` must be the EXACT value from handover. It is used to decrypt the database connection passwords. A wrong/different key = "Invalid decryption key" errors and broken charts.

---

## 5. Set Up Local PostgreSQL (Superset's metadata DB)

Open a terminal with `psql` access (or use pgAdmin).

```powershell
# Set postgres superuser password prompt may appear
psql -U postgres
```

Inside psql, run:
```sql
CREATE USER superset_user WITH PASSWORD 'password';
CREATE DATABASE superset OWNER superset_user;
GRANT ALL PRIVILEGES ON DATABASE superset TO superset_user;
\q
```

### Restore the database backup (file received during handover)

```powershell
$env:PGPASSWORD = "password"
psql -U superset_user -h localhost -d superset -f "superset_backup_PRODUCTION_READY_XXXX.sql"
```

Verify the restore:
```powershell
psql -U superset_user -h localhost -d superset -c "SELECT COUNT(*) FROM dashboards;"
# Should return 2
```

> **DO NOT** run `superset db upgrade` or `superset init` after restoring. The backup already has the correct schema and data. Running those commands will corrupt the restored state.

---

## 6. Apply Custom Branding + AI Chat Widget

The repo includes custom templates in `custom_templates/`. Copy them into the installed Superset package:

```powershell
# Custom HTML templates (logo replacement + AI chat widget)
copy custom_templates\tail_js_custom_extra.html venv_310\Lib\site-packages\superset\templates\
copy custom_templates\head_custom_extra.html venv_310\Lib\site-packages\superset\templates\

# Logo + favicon images
copy static\assets\samarthx_logo.png venv_310\Lib\site-packages\superset\static\assets\images\
copy static\assets\SXfavicon.svg venv_310\Lib\site-packages\superset\static\assets\images\
```

---

## 7. Start Superset

You can start both **n8n** and **Superset** together using the automated startup script:
```powershell
.\start_dev.ps1
```

Alternatively, to start Superset manually (make sure venv is activated):
```powershell
$env:SUPERSET_CONFIG_PATH = "$PWD\superset_config.py"

# If superset.exe is blocked or has launcher path issues, run via the helper script:
python run_superset.py run -p 5000 --with-threads --reload

# Otherwise run the default command:
# superset run -p 5000 --with-threads --reload
```

Open **http://127.0.0.1:5000**

You should see:
- SamarthX logo (top-left)
- Login screen
- After login: 2 dashboards with charts

> If you get "Invalid decryption key" → your SECRET_KEY in `.env` doesn't match. Fix it.

---

## ✅ At this point, Superset is fully working (dashboards + charts).

The AI chat (Part 8 below) is optional and needs n8n + Gemini API Key.

---

## 8. AI Chat Setup (Optional but recommended)

The chat widget is already embedded (from step 6). It needs n8n + Google Gemini API Key.

### 8a. Get a Gemini API Key
Obtain a Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/).
Create the key and save it. You will configure this key in your n8n workflow.

### 8b. Install and start n8n
```powershell
npm install -g n8n
n8n start
```
Open **http://localhost:5678** and complete the owner account setup (first launch only).

### 8c. Import the workflow
In a new terminal (keep n8n running):
```powershell
cd path\to\superset
n8n import:workflow --input=ai_integration\n8n_workflow.json
```

### 8d. Create the two database credentials in n8n

In the n8n UI (http://localhost:5678):
**Credentials → Add Credential → Postgres**. Create BOTH:

**Credential 1:**
| Field | Value |
|-------|-------|
| Name | `SamarthX Data DB` (exact) |
| Host | `172.16.0.119` |
| Database | `employee_db` |
| User | `dashboard_read_only_user` |
| Password | (from handover) |
| Port | `5432` |
| SSL | disable |

**Credential 2:**
| Field | Value |
|-------|-------|
| Name | `SamarthX Org DB` (exact) |
| Host | `172.16.0.119` |
| Database | `org_db` |
| User | `dashboard_read_only_user` |
| Password | (from handover) |
| Port | `5432` |
| SSL | disable |

> Names must match EXACTLY - the workflow links credentials by name.

### 8e. Link credentials and activate
1. Open the **SamarthX AI Chat** workflow in n8n
2. Click the **Query Employee DB** node → set credential to `SamarthX Data DB`
3. Click the **Query Org DB** node → set credential to `SamarthX Org DB`
4. Toggle **Active** (top-right switch) to ON
5. Save

### 8f. Test the AI
```powershell
curl -X POST http://localhost:5678/webhook/ai-chat -H "Content-Type: application/json" -d "{\"question\": \"How many teachers are in Goa?\"}"
```
Expected:
```json
{"answer": "There are 14,376 teachers in Goa."}
```

> **Requires network access to 172.16.0.119.** If you're off-site, connect the VPN first. Test with:
> ```powershell
> Test-NetConnection -ComputerName 172.16.0.119 -Port 5432
> ```

### 8g. Use it in Superset
1. Refresh Superset (Ctrl+Shift+R)
2. Log in
3. Click the **💬 button** (bottom-right)
4. Ask questions like:
   - "How many teachers are in Goa?"
   - "How many female teaching staff?"
   - "How many schools are onboarded?"
   - "How many government schools?"

Responses from Gemini are fast and processed on Google's hosted infrastructure.

---

## Daily Startup (after first setup)

You can launch both n8n and Superset with a single command:
```powershell
.\start_dev.ps1
```

If you prefer starting them manually in separate windows:
```powershell
# Terminal 1: n8n

# Terminal 2: n8n
n8n start

# Terminal 3: Superset
cd path\to\superset
.\venv_310\Scripts\Activate.ps1
$env:SUPERSET_CONFIG_PATH = "$PWD\superset_config.py"
python run_superset.py run -p 5000 --with-threads --reload
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "Invalid decryption key" | Wrong SECRET_KEY | Use exact key from handover in `.env` |
| Charts show DB error | Network to 172.16.0.119 down | Connect VPN |
| Logo not showing | Templates not copied | Redo step 6 |
| Chat button missing | Widget not copied / on login page | Redo step 6; button only shows after login |
| Chat "Error connecting" | n8n not running | `n8n start` |
| Chat returns nothing | n8n credential missing | Create credentials (step 8d) |
| Gemini API Error | API key wrong/missing | Paste a valid Google AI Studio API key in the n8n HTTP Request nodes |

For deeper issues see `PRODUCTION_TROUBLESHOOTING.md`.

---

## Important Rules

1. **NEVER change `SUPERSET_SECRET_KEY`** - breaks encrypted DB passwords
2. **NEVER run `superset db upgrade` / `superset init`** after restoring backup
3. **NEVER commit `.env`** to git (it's gitignored - keep it that way)
4. Keep Superset version at **6.0.0**
5. Back up before any DB change: `pg_dump -U superset_user superset > backup.sql`

---

## Reference

| Service | URL / Detail |
|---------|--------------|
| Superset | http://127.0.0.1:5000 |
| n8n | http://localhost:5678 |
| Gemini API | https://generativelanguage.googleapis.com |
| Data DB | 172.16.0.119:5432 (employee_db, org_db) |
| Metadata DB | localhost:5432/superset |
| AI model | gemini-2.5-flash |

Other docs:
- `ai_integration/README.md` - AI chat architecture
- `ai_integration/schema_prompt.md` - the DB schema + AI prompt
- `DEPLOYMENT_GUIDE.md` - production deployment
- `PRODUCTION_TROUBLESHOOTING.md` - common production issues
