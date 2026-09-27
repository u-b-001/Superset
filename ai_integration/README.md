# SamarthX AI Chat Integration

Natural Language → Dashboard Insights for Superset using n8n + **Groq Cloud (`llama-3.1-8b-instant`)** for ultra-fast, sub-second responses.

Ask questions in plain English, get answers from your data instantly.

---

## How It Works

```
User types question in chat widget (inside Superset)
        ↓
SLM Input Guardrail (blocks injections, malicious queries)
        ↓
n8n webhook receives sanitized question
        ↓
Groq Llama-3.1-8b-instant converts question → SQL (~0.2s)
        ↓
SQL safety validation (SELECT-only)
        ↓
PostgreSQL runs query (read-only user)
        ↓
Groq Llama-3.1-8b-instant formats result → plain English (~0.2s)
        ↓
Answer appears in chat widget (Total response time < 1s)
```

AI requests are sent to **Groq Cloud API** using free, high-speed LPU hardware.

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

### Step 1: Get a Gemini API Key
Obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/).
Configure this key in both HTTP Request nodes in n8n.

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
| Gemini API | Google Cloud | 443 | Google Gemini 2.5 Flash |
| PostgreSQL (data) | 172.16.0.119 | 5432 | The actual data |

---

## Safety & Guardrail Features

1. **Open-Source SLM Input Guardrail** (`ai_integration/guardrails.py`):
   - **Layer 1: Heuristic Pattern Engine (<1ms)**: Blocks prompt injections (`ignore previous instructions`), SQL mutations (`DROP`, `ALTER`, `TRUNCATE`, `UPDATE`), and system prompt exfiltration.
   - **Layer 2: Local SLM Semantic Classifier**: Evaluates input scope and malicious intent using local **Ollama** (`gemma2:2b`, `llama3.1:8b`) with zero API costs.
   - **Graceful Fallback**: If Ollama is offline or times out, the system automatically falls back to Layer 1 heuristics without blocking legitimate queries.
2. **Read-only DB user** (`dashboard_read_only_user`) - cannot modify data.
3. **SQL keyword blocking** - INSERT/UPDATE/DELETE/DROP rejected in n8n and Superset proxy.
4. **SELECT-only enforcement** - queries must start with SELECT.
5. **Row limit** - auto LIMIT 1000 on non-aggregate queries.
6. **Secure API Key** - requests are authenticated directly via Google AI Studio API.

---

## Privacy Note

Only the **database schema** (table/column names) is sent to the LLM, plus the
query results for formatting. Since Gemini is hosted, schema and queries are sent to
Google's cloud API. Ensure compliance with your organization's data privacy policies.

---

## Production Deployment

When deploying to 172.16.0.106:
1. Configure the Gemini API key in n8n on the production server
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
- [ ] Get Gemini API Key
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
