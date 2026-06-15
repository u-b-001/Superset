# SamarthX AI Chat Integration

Natural Language → Dashboard Insights for Superset using n8n + Ollama (local LLM).

Ask questions in plain English, get answers from your data.

---

## How It Works

```
User types question in chat widget (inside Superset)
        ↓
n8n webhook receives it
        ↓
Ollama (qwen2.5-coder) converts question → SQL
        ↓
SQL safety validation (SELECT-only)
        ↓
PostgreSQL runs query (read-only user)
        ↓
Ollama formats result → plain English
        ↓
Answer appears in chat widget
```

All AI runs **locally** (Ollama) - no data sent to cloud. Good for government data privacy.

---

## Files in This Folder

| File | Purpose |
|------|---------|
| `README.md` | This overview |
| `schema_prompt.md` | Database schema + system prompt for the AI |
| `n8n_workflow_guide.md` | Step-by-step n8n workflow setup (7 nodes) |
| `chat_widget.html` | Chat UI to embed in Superset |

---

## Setup Order

### Step 1: Pull the AI model
```bash
ollama pull qwen2.5-coder:7b
```
Verify:
```bash
ollama run qwen2.5-coder:7b "count rows in employees table in postgres"
```

### Step 2: Start n8n
```bash
n8n start
```
Open http://localhost:5678

### Step 3: Build the n8n workflow
Follow `n8n_workflow_guide.md` - create the 7-node workflow.
Use the system prompt from `schema_prompt.md`.

### Step 4: Test the webhook (no UI yet)
```bash
curl -X POST http://localhost:5678/webhook/ai-chat \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"How many teaching staff are there?\"}"
```

### Step 5: Add the chat widget to Superset
1. Open `chat_widget.html`
2. Update `N8N_WEBHOOK_URL` to your webhook URL
3. Append its content to:
   `venv_310/Lib/site-packages/superset/templates/tail_js_custom_extra.html`
   (after the existing logo script)
4. Refresh Superset - the chat button appears bottom-right

---

## Architecture Components

| Component | Where | Port | Purpose |
|-----------|-------|------|---------|
| Superset | local / 172.16.0.106 | 8088 | Dashboards + chat widget |
| n8n | local / server | 5678 | Workflow orchestration |
| Ollama | local / server | 11434 | Local LLM |
| PostgreSQL (data) | 172.16.0.119 | 5432 | The actual data |

---

## Safety Features

1. **Read-only DB user** (`dashboard_read_only_user`) - cannot modify data
2. **SQL keyword blocking** - INSERT/UPDATE/DELETE/DROP rejected in n8n
3. **SELECT-only enforcement** - queries must start with SELECT
4. **Row limit** - auto LIMIT 1000 on non-aggregate queries
5. **Local LLM** - data never leaves your infrastructure

---

## Privacy Note

Only the **database schema** (table/column names) is sent to the LLM, plus the
query results for formatting. Since Ollama runs locally, even that stays on your
server. No external API calls. Ideal for government/sensitive data.

---

## Production Deployment

When deploying to 172.16.0.106:
1. Install Ollama on the server, pull the model
2. Install n8n on the server (or a dedicated VM)
3. Import the n8n workflow
4. Copy `tail_js_custom_extra.html` (with chat widget) to the server's venv
5. Update `N8N_WEBHOOK_URL` to the production n8n URL
6. Add n8n origin to CORS_OPTIONS in superset_config.py if needed

---

## Roadmap

- [x] Schema extracted
- [x] System prompt written
- [x] n8n workflow guide
- [x] Chat widget built
- [ ] Pull model
- [ ] Build n8n workflow
- [ ] Test webhook
- [ ] Embed widget
- [ ] Tune prompt accuracy
- [ ] Deploy to production

---

## Future Enhancements

- Show the generated SQL (transparency toggle)
- Render results as charts, not just text
- Conversation memory (follow-up questions)
- Multi-database routing (employee_db + org_db)
- User access control (who can use AI chat)
- Query logging for audit
