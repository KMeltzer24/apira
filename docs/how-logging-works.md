# How Logging Works (Phase IV)

This doc explains **structured logging** across Apira: JSON events, `X-Request-ID`
correlation, redaction, and how to follow one user action from browser to RDS.

**Contract (schema + rules):** [logging.md](logging.md)  
**Demo:** [demo-logging.md](demo-logging.md)

**Related repos:**

| Repo | What it logs |
|------|----------------|
| [apira](https://github.com/KMeltzer24/apira) (this repo) | `user-service`, `portfolio-service` HTTP + login/portfolio events |
| [apira-agent](https://github.com/KMeltzer24/apira-agent) | `/chat` HTTP, agent build/run, MCP tool calls |
| [apira-mcp](https://github.com/KMeltzer24/apira-mcp) | MCP tool lifecycle + upstream backend calls |
| [apira-rag](https://github.com/KMeltzer24/apira-rag) | Research tools, search, ingest, embed, PDF extract |
| [apira-frontend](https://github.com/KMeltzer24/apira-frontend) | Browser console JSON + `X-Request-ID` on every API call |

This is the observability baseline for the future **production-incident resolution
agent**. Today logs stay in the browser console and container stdout. CloudWatch,
OpenTelemetry, dashboards, alerts, and auto-remediation come later.

---

## The big picture

```text
Browser (DevTools Console)
  │  apiFetch() creates UUID → X-Request-ID
  ▼
┌─────────────────────────────────────────────────────────────┐
│ EC2 containers — same request_id in every JSON line         │
│                                                             │
│  apira-agent (:8100)                                        │
│       │                                                     │
│       ├── apira-mcp (:8000)                                 │
│       │     ├── user-service (:8001) → RDS                  │
│       │     └── portfolio-service (:8002) → RDS             │
│       │                                                     │
│       └── apira-rag (:8200)                                 │
│             ├── stock-research/ (local search)              │
│             └── research_chunks / Gemini embeddings         │
└─────────────────────────────────────────────────────────────┘
```

One UUID ties the whole path together. You copy it from a response header or a
log line, then `grep` it in each service.

---

## What we built

| Piece | Where | Role |
|-------|-------|------|
| Shared JSON schema | [logging.md](logging.md) | Required fields + redaction rules |
| Browser logger | `apira-frontend/src/lib/logger.js` | Structured `console.*` events |
| API wrapper | `apira-frontend/src/lib/api.js` | Generates/sends `X-Request-ID`, times requests |
| Backend middleware | `*/logging_config.py` | Accept/echo ID, request lifecycle logs |
| Agent logging | `apira-agent/logging_config.py` + `server.py` / `agent.py` | Chat + MCP tool events; ID to both MCP servers |
| MCP / RAG logging | `apira_logging.py` + `request_logging.py` | Tool + upstream / RAG pipeline events |

Every service supports:

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json      # or text for local debugging
ENVIRONMENT=development
```

---

## Step-by-step: one Agent Chat request

1. **Frontend** (`apiFetch`) creates a UUID, sets `X-Request-ID`, logs
   `http_request_started` in the browser console (path, method, upstream —
   never the prompt body).

2. **apira-agent** accepts that UUID (or generates one), echoes it on the
   response, and logs `http.request.started` / `chat.started` with
   `message_length` only.

3. **Agent run** logs `agent.run.started`, then each MCP tool as
   `mcp.tool.started` with `tool_name` and `argument_keys` (names only).

4. **apira-mcp** receives the same ID, logs tool start/complete, and forwards
   the ID to user/portfolio services on upstream HTTP calls.

5. **user-service / portfolio-service** log business events
   (`login_succeeded`, `portfolio_fetched`) and `request_completed` with
   status and duration — still under the same `request_id`.

6. If the prompt used research tools, **apira-rag** logs search/ingest events
   with counts and filenames, not document text or vectors.

7. **Frontend** logs `http_request_completed` with status and `duration_ms`.

Copy the response `X-Request-ID` and search every container for that value —
that is the full story of one request.

---

## What appears in a log line

Every application event is one JSON object:

```json
{
  "timestamp": "2026-07-22T18:13:25.128527Z",
  "level": "INFO",
  "service": "apira-agent",
  "environment": "development",
  "event": "mcp.tool.started",
  "message": "MCP tool call started",
  "request_id": "77d615cc-8313-4dbe-947d-bbec21753f2f",
  "tool_name": "login",
  "upstream": "apira",
  "argument_keys": ["password", "username"]
}
```

Safe extras you will see often: `method`, `path`, `status_code`, `duration_ms`,
`user_id`, `holdings_count`, `match_count`, `model`, `error_type`.

---

## What never appears

- Passwords, API keys, tokens, DB URLs
- Full prompts or agent replies
- Tool argument **values** (only key names)
- Usernames in application events (prefer `user_id`)
- Full portfolio holdings lists (prefer `holdings_count`)
- Research file contents, embeddings, or raw query text in request logs

That keeps the trail useful for demos and debugging without leaking secrets.

---

## Where to look

| Surface | How |
|---------|-----|
| Browser | DevTools → Console (JSON strings) and Network → response header `x-request-id` |
| Agent | `cd ~/apira-agent && sudo docker compose logs -f agent` |
| Backend MCP | `cd ~/apira-mcp && sudo docker compose logs -f mcp-server` |
| Research MCP | `cd ~/apira-rag && sudo docker compose logs -f rag-server` |
| Backend APIs | `cd ~/apira && sudo docker compose -f docker-compose.backend.yml logs -f` |

Filter one request:

```bash
sudo docker compose logs --since=10m | grep '<request-id>'
```

---

## Direct API path (no agent)

The Portfolio tab calls user-service and portfolio-service directly. The frontend
still sends `X-Request-ID`; only those backend containers will have matching
lines. Agent Chat / Recommender use the longer path above.

---

## Further reading

- [logging.md](logging.md) — canonical schema and redaction contract
- [demo-logging.md](demo-logging.md) — demo walkthrough
- [deploy-ec2.md](deploy-ec2.md) — “Follow a request through logs”
- [architecture.md](architecture.md) — system diagram + observability note
