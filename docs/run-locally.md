# Run Apira locally

This is the path for Promptfoo and local demos on your Mac.

Grafana Cloud Loki is still used (free tier). It is not AWS. Copy Loki credentials into `.env.observability`.

## What this repo starts

From the **apira** repo root:

```bash
cp .env.observability.example .env.observability
# set GRAFANA_LOKI_URL, GRAFANA_LOKI_USER, GRAFANA_LOKI_API_KEY
# (Grafana Cloud → Loki → Send logs). Leave them blank to skip cloud push;
# log-service still accepts browser logs on :8300.

docker compose -f docker-compose.local.yml --env-file .env.observability up -d --build
```

| Container | Port | Role |
|-----------|------|------|
| postgres | `5432` | `users` / `portfolios` (seeded alice & bob) |
| user-service | `8001` | `POST /login` |
| portfolio-service | `8002` | `GET /portfolio?user_id=` |
| log-service | `8300` | Browser logs → file + Grafana Cloud Loki |
| Grafana Alloy | — | Docker stdout → Loki |

Demo logins: `alice` / `password`, `bob` / `password`.

Seed SQL runs **only on first Postgres volume create**. To re-seed: `docker compose -f docker-compose.local.yml down -v` then `up` again.

Check:

```bash
curl -s -X POST http://localhost:8001/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"password"}'
# {"success":true,"username":"alice","user_id":1}
```

## Sibling repos (same machine)

Use `host.docker.internal` so containers can reach ports published on the Mac.

**MCP** ([apira-mcp](https://github.com/KMeltzer24/apira-mcp)) — `.env`:

```bash
USER_SERVICE_URL=http://host.docker.internal:8001
PORTFOLIO_SERVICE_URL=http://host.docker.internal:8002
```

```bash
cd ~/development/apira-mcp && docker compose up -d --build
```

**RAG** ([apira-rag](https://github.com/KMeltzer24/apira-rag)) — local folder search does not need embeddings. Point `DATABASE_URL` at local Postgres anyway so the process can start; skip ingest unless you want Vector DB.

```bash
DATABASE_URL=postgresql+psycopg2://apira:apira@host.docker.internal:5432/apira
GOOGLE_API_KEY=<gemini-key>   # only required for searchVectorDB / ingest
```

```bash
cd ~/development/apira-rag && docker compose up -d --build
```

On the Recommender tab, choose **Local folder** (`searchLocalFolder`). **Vector DB** needs a later `ingest_research.py` into this Postgres (pgvector image is already used).

**Agent** ([apira-agent](https://github.com/KMeltzer24/apira-agent)) — `.env`:

```bash
TOOL_MODE=mcp   # or python | skills_prompt | skills_shell — see apira-agent docs/tool-use-scenarios.md
MCP_URL=http://host.docker.internal:8000/mcp
RAG_MCP_URL=http://host.docker.internal:8200/mcp
USER_SERVICE_URL=http://host.docker.internal:8001
PORTFOLIO_SERVICE_URL=http://host.docker.internal:8002
STOCK_RESEARCH_DIR=/data/stock-research
GOOGLE_API_KEY=<gemini-key>
```

```bash
cd ~/development/apira-agent && docker compose up -d --build
```

When switching `TOOL_MODE`, pass it on the compose command (shell exports override `.env`): `TOOL_MODE=python docker compose up -d --force-recreate`. Vector Recommender needs `TOOL_MODE=mcp`.

promptfoo (and curl) use:

```text
http://localhost:8100/chat
```

### Promptfoo evals

With the agent healthy, from the **apira-agent** repo:

```bash
curl -s http://localhost:8100/health
REQUEST_TIMEOUT_MS=180000 promptfoo eval
```

Config: [apira-agent/promptfooconfig.yaml](https://github.com/KMeltzer24/apira-agent/blob/main/promptfooconfig.yaml). Scores the full multi-agent `reply` (chat, alice portfolio, local-folder recommender, vector-DB recommender).

Optional HTML report after an eval:

```bash
promptfoo view
```

## Demo checklist

1. **Architecture** — [architecture.md](architecture.md): supervisor → portfolio / research; MCP tools, not every service as an agent.
2. **UI** — `http://localhost:3000`: Agent Chat, Recommender (**Local folder**), Portfolio (`alice` / `password`).
3. **Multi-agent** — point at `apira-agent/agents/graph.py` (`START → supervisor → portfolio|research → END`).
4. **Promptfoo** — from `apira-agent`: `REQUEST_TIMEOUT_MS=180000 promptfoo eval` (expect 4/4 pass after ingest) or `promptfoo view`. Demo notes: [apira-agent/docs/promptfoo.md](https://github.com/KMeltzer24/apira-agent/blob/main/docs/promptfoo.md).
5. **Logs (optional)** — Grafana Explore, `{service="apira-agent"}` or a shared `request_id`.

**Frontend** ([apira-frontend](https://github.com/KMeltzer24/apira-frontend)) — `.env` then rebuild (Vite bakes `VITE_*` at build time):

```bash
VITE_USER_SERVICE_URL=http://localhost:8001
VITE_PORTFOLIO_SERVICE_URL=http://localhost:8002
VITE_AGENT_URL=http://localhost:8100
VITE_LOG_SERVICE_URL=http://localhost:8300
```

```bash
cd ~/development/apira-frontend && docker compose up -d --build
```

Open [http://localhost:3000](http://localhost:3000).

## Grafana

1. Grafana Cloud → **Explore** → Loki.
2. Filter `environment="development"` (local compose sets that).
3. Search `{service="apira-agent"}` or a `request_id` from the browser console.

If Loki credentials are missing, Alloy/log-service still run; cloud push is skipped (log-service warns). Browser logs remain in the `log-service` volume.

## Stock Recommender

**Local folder** works without ingest. **Vector DB** needs `ingest_research.py` in apira-rag against local Postgres (already done if `research_chunks` has rows). Both modes are covered by Promptfoo tests 3 and 4.

## Stop

```bash
docker compose -f docker-compose.local.yml down
# add -v to wipe Postgres seed/data
```

Stop MCP, RAG, agent, and frontend the same way in each repo (`docker compose down`).
