# n8n Workflow Setup Guide - Text-to-SQL AI Chat

Step-by-step to build the AI chat workflow in n8n.

---

## Prerequisites Checklist

- [ ] Ollama running (port 11434) with model pulled
- [ ] n8n running (port 5678)
- [ ] PostgreSQL data source reachable (172.16.0.119)
- [ ] Network/VPN connected to reach data source

### Pull the model first:
```bash
ollama pull qwen2.5-coder:7b
```

### Verify model works:
```bash
ollama run qwen2.5-coder:7b "Write a PostgreSQL query to count rows in a table named employees"
```

---

## Workflow Overview

```
Webhook → Build Prompt → Ollama (text→SQL) → Validate SQL → 
PostgreSQL → Ollama (format answer) → Respond
```

7 nodes total.

---

## NODE-BY-NODE SETUP

### Node 1: Webhook (Trigger)
- Type: **Webhook**
- HTTP Method: **POST**
- Path: `ai-chat`
- Respond: **Using Respond to Webhook node**

This gives you a URL like: `http://localhost:5678/webhook/ai-chat`

Expected incoming JSON:
```json
{ "question": "How many female teachers are in Goa?" }
```

---

### Node 2: Set (Build the prompt)
- Type: **Edit Fields (Set)**
- Add field `prompt` (string) = the full system prompt + user question

Or use a Code node:
```javascript
const systemPrompt = `You are a PostgreSQL expert for the SamarthX education database...
[paste full system prompt from schema_prompt.md]`;

const question = $input.first().json.body.question;

return [{
  json: {
    question: question,
    fullPrompt: systemPrompt + "\n\nUser question: " + question
  }
}];
```

---

### Node 3: HTTP Request (Ollama - Generate SQL)
- Type: **HTTP Request**
- Method: **POST**
- URL: `http://localhost:11434/api/generate`
- Body (JSON):
```json
{
  "model": "qwen2.5-coder:7b",
  "prompt": "={{ $json.fullPrompt }}",
  "stream": false,
  "options": { "temperature": 0 }
}
```

Response contains the SQL in `response` field.

---

### Node 4: Code (Validate SQL - SAFETY)
- Type: **Code**

```javascript
let sql = $input.first().json.response.trim();

// Strip markdown code fences if present
sql = sql.replace(/```sql/gi, '').replace(/```/g, '').trim();

// SAFETY: block dangerous keywords
const forbidden = /\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXECUTE)\b/i;
if (forbidden.test(sql)) {
  throw new Error('Unsafe SQL blocked: ' + sql);
}

// Must start with SELECT
if (!/^\s*SELECT/i.test(sql)) {
  throw new Error('Only SELECT queries allowed: ' + sql);
}

// Enforce a hard row cap if no LIMIT and not an aggregate
if (!/LIMIT/i.test(sql) && !/COUNT|SUM|AVG|MIN|MAX|GROUP BY/i.test(sql)) {
  sql = sql.replace(/;?\s*$/, '') + ' LIMIT 1000';
}

return [{ json: { sql: sql, question: $('Set').first().json.question } }];
```

---

### Node 5: Postgres (Run the query)
- Type: **Postgres**
- Operation: **Execute Query**
- Query: `={{ $json.sql }}`

**Credentials (create new):**
- Host: `172.16.0.119`
- Database: `employee_db`  (use `org_db` for school questions)
- User: `dashboard_read_only_user`
- Password: `Zup1!whb`  (the read-only password)
- Port: `5432`
- SSL: as required

> Use the READ-ONLY user. It physically cannot modify data - defense in depth.

---

### Node 6: HTTP Request (Ollama - Format answer)
- Type: **HTTP Request**
- Method: **POST**
- URL: `http://localhost:11434/api/generate`
- Body (JSON):
```json
{
  "model": "qwen2.5-coder:7b",
  "prompt": "The user asked: {{ $('Code').first().json.question }}\n\nThe query returned this data: {{ JSON.stringify($json) }}\n\nWrite a short, clear, natural-language answer for a non-technical user. Be concise.",
  "stream": false,
  "options": { "temperature": 0.3 }
}
```

---

### Node 7: Respond to Webhook
- Type: **Respond to Webhook**
- Respond With: **JSON**
- Body:
```json
{ "answer": "={{ $json.response }}" }
```

---

## TESTING (before building UI)

Use Postman or curl:

```bash
curl -X POST http://localhost:5678/webhook/ai-chat \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"How many teaching staff are there?\"}"
```

Expected response:
```json
{ "answer": "There are 1,234 teaching staff members in Goa schools." }
```

---

## Handling Two Databases

Since `employees` is in `employee_db` and `schools` is in `org_db`:

**Option A (simplest):** Add a routing step - if question mentions "school", use org_db credentials; otherwise employee_db.

**Option B:** Set up PostgreSQL foreign data wrapper (postgres_fdw) so one connection can query both.

**Option C:** Two separate Postgres nodes + an IF node to route.

For MVP, start with `employee_db` only (most questions are about employees/teachers).

---

## Common Issues

| Problem | Fix |
|---------|-----|
| Ollama slow | Normal on CPU. Use smaller model or add GPU |
| SQL has markdown fences | Node 4 strips them |
| Connection timeout to .119 | Check VPN/network |
| Wrong table errors | Improve schema prompt detail |
| AI hallucinerates columns | Add example queries to prompt |

---

## Next Step

Once this webhook returns correct answers, build the chat widget (see `chat_widget.html`) and connect it to this webhook URL.
