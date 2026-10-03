# Apira

Local multi-service portfolio assistant. A user logs in, reads holdings, and asks a multi-agent system for stock research.

This repository is the backend: two FastAPI services and PostgreSQL in Docker, plus log ingest to Grafana Cloud. The UI, agent, MCP tools, and research corpus are separate repos and call these APIs on `localhost`.

**Stack:** Python, FastAPI, PostgreSQL, Docker, Grafana Cloud Loki.

**Run locally:** [docs/run-locally.md](docs/run-locally.md) — Postgres seed, backends, log-service, Alloy → Loki.

| Repo | Role |
|------|------|
| [apira-frontend](https://github.com/KMeltzer24/apira-frontend) | React UI (portfolio, agent chat, recommender) |
| [apira-agent](https://github.com/KMeltzer24/apira-agent) | LangGraph supervisor (`8100`) plus A2A portfolio and research specialists, Nacos (`8848`) |
| [apira-mcp](https://github.com/KMeltzer24/apira-mcp) | Login, holdings, and last-recommendation tools |
| [apira-rag](https://github.com/KMeltzer24/apira-rag) | Research corpus, pgvector search, Gemini embeddings |

## Services

| Service | Port | Description |
|---------|------|-------------|
| **user-service** | `8001` | `POST /login` — validates credentials against the `users` table |
| **portfolio-service** | `8002` | `GET /portfolio?user_id=<id>` — returns per-user holdings from the `portfolios` table |
| **log-service** | `8300` | Browser log ingest → local JSONL + Grafana Cloud Loki |
| **Grafana Alloy** | — | Docker stdout → Grafana Cloud Loki |

Demo logins (seed data): `alice` / `password`, `bob` / `password`.

The backend MCP server (port `8000`) lives in [apira-mcp](https://github.com/KMeltzer24/apira-mcp) and wraps the two APIs above. Research tools, corpus, and pgvector ingestion live in [apira-rag](https://github.com/KMeltzer24/apira-rag) on port `8200`.

## Project Structure

```
apira/
├── user-service/
├── portfolio-service/
├── log-service/
├── observability/                 # Grafana Alloy config
├── sql/local-seed.sql             # alice/bob for local Postgres
├── docker-compose.local.yml       # Mac: Postgres + backends + Loki shippers
├── docker-compose.observability.yml
├── docs/run-locally.md
├── docs/architecture.md
├── docs/grafana-cloud.md
├── docs/how-the-database-works.md
├── docs/how-logging-works.md
├── docs/logging.md
├── apira.postman_collection.json
└── README.md
```

## Architecture

See **[docs/architecture.md](docs/architecture.md)** for the full system diagram (frontend, agent, MCP, backend, Postgres, Gemini, Grafana).

**Run locally:** [docs/run-locally.md](docs/run-locally.md).

**Logging:** [docs/how-logging-works.md](docs/how-logging-works.md) · [docs/logging.md](docs/logging.md) · [docs/grafana-cloud.md](docs/grafana-cloud.md).

**Demo checklist:** [docs/run-locally.md](docs/run-locally.md) — UI, multi-agent graph, Promptfoo, and a shared `request_id` in Grafana.

**Stock Recommender:** [apira-rag/docs/how-stock-recommender-works.md](https://github.com/KMeltzer24/apira-rag/blob/main/docs/how-stock-recommender-works.md) — local folder + pgvector search.

## API Endpoints

### User Service — `POST /login`

Request:

```json
{ "username": "alice", "password": "password" }
```

Success (`200`):

```json
{ "success": true, "username": "alice", "user_id": 1 }
```

Invalid credentials return `401`.

### Portfolio Service — `GET /portfolio?user_id=<id>`

Returns holdings for that user only (`alice` and `bob` have different portfolios). Example response for `user_id=1`:

```json
{
  "holdings": [
    { "ticker": "AAPL", "company": "Apple Inc.", "shares": 150 },
    { "ticker": "MSFT", "company": "Microsoft Corp.", "shares": 80 },
    { "ticker": "GOOGL", "company": "Alphabet Inc.", "shares": 25 },
    { "ticker": "AMZN", "company": "Amazon.com Inc.", "shares": 40 },
    { "ticker": "TSLA", "company": "Tesla Inc.", "shares": 60 }
  ]
}
```

## Testing

Import `apira.postman_collection.json` into Postman — service URLs are set as collection variables.

## Database

Both backend services connect to **PostgreSQL** via **SQLAlchemy 2.x** and the **psycopg2** driver — not Microsoft SQL Server. See **[docs/how-the-database-works.md](docs/how-the-database-works.md)** for connection setup, request flow, and which imports are current vs legacy.

Local Compose seeds `alice` / `bob` from `sql/local-seed.sql`. Sibling services: [apira-mcp](https://github.com/KMeltzer24/apira-mcp), [apira-rag](https://github.com/KMeltzer24/apira-rag), [apira-agent](https://github.com/KMeltzer24/apira-agent).
