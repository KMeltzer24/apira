# Structured Logging — Contract

Schema and redaction rules for Apira application logs. This is the **spec**
(what every service must emit), not a how-to.

**How it works (narrative):** [how-logging-works.md](how-logging-works.md)  
**Grafana Cloud setup:** [grafana-cloud.md](grafana-cloud.md)

## Correlation

Every HTTP request uses the `X-Request-ID` header:

1. The caller sends a UUID.
2. A service accepts a valid incoming ID or generates one.
3. The service includes the ID in its logs and response header.
4. Calls to downstream services reuse the same ID.

For agent requests, the ID flows:

```text
frontend → apira-agent → apira-mcp → user/portfolio service
                       └→ apira-rag → Gemini/RDS
```

## Required fields

Each application log is one JSON object with these fields:

- `timestamp` — UTC ISO-8601 timestamp
- `level` — `DEBUG`, `INFO`, `WARNING`, or `ERROR`
- `service` — emitting service / component name
- `environment` — deployment environment
- `event` — stable machine-readable event name
- `message` — short human-readable description
- `request_id` — correlation ID when a request is active

When known, also include:

- `user_id` — numeric user id for Alice-style lookbacks across requests
- `tickers` / `holdings_summary` — portfolio tickers (and share counts) on
  portfolio / recommender paths

Events add other safe fields such as `method`, `path`, `status_code`,
`duration_ms`, `tool_name`, `upstream`, `match_count`, `chunk_count`,
`error_type`, and `error_code`.

## Redaction rules

Never log:

- Passwords, API keys, authorization headers, or database credentials
- Full prompts, agent replies, HTTP request/response bodies, or tool argument values
- Research document text, extracted page text, or embedding vectors

Log metadata instead: payload length, argument names, `user_id`, ticker lists,
holdings summary (`ticker` + `shares`), filename, page/chunk count, model name,
status, and duration. Search query text is omitted from request/tool logs;
diagnostic RAG events may include only a short normalized preview.

Central collection uses **Grafana Cloud Loki**:

- Container stdout → Grafana Alloy on EC2 → Loki
- Browser events → `log-service` (`:8300`) → local JSONL + Loki

See [grafana-cloud.md](grafana-cloud.md) for credentials, deploy, and LogQL.

## Configuration

Python services support:

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
ENVIRONMENT=development
```

`LOG_FORMAT=text` is available for local debugging. Docker keeps JSON on
stdout so Alloy can ship the same events without changing application code.

Frontend (Vite):

```bash
VITE_LOG_LEVEL=INFO
VITE_ENVIRONMENT=development
VITE_LOG_SERVICE_URL=http://<EC2_IP>:8300
```

## Viewing logs

Prefer Grafana Explore with LogQL (see [grafana-cloud.md](grafana-cloud.md)).

Fallback on the host:

```bash
docker compose logs -f
docker compose logs --since=10m
```

Browser events still appear in DevTools Console. Copy a response's
`X-Request-ID` and search Grafana (or container logs) for the same value.
