# Phase IV — Structured Logging

Apira emits structured JSON logs so one user action can be followed across the
frontend, agent, MCP servers, backend APIs, Gemini, and PostgreSQL.

This is the baseline for the future production-incident resolution agent. Logs
currently go to the browser console or container stdout; centralized collection,
metrics, traces, alerting, and automated remediation are later phases.

**How it works (narrative):** [how-logging-works.md](how-logging-works.md)  
**Demo:** [demo-logging.md](demo-logging.md)

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
- `service` — emitting service name
- `environment` — deployment environment
- `event` — stable machine-readable event name
- `message` — short human-readable description
- `request_id` — correlation ID when a request is active

Events add safe fields such as `method`, `path`, `status_code`, `duration_ms`,
`tool_name`, `upstream`, `match_count`, `chunk_count`, `error_type`, and
`error_code`.

## Redaction rules

Never log:

- Passwords, API keys, authorization headers, or database credentials
- Full prompts, agent replies, HTTP request/response bodies, or tool arguments
- Usernames or complete portfolio data
- Research document text, extracted page text, or embedding vectors

Log metadata instead: payload length, argument names, user ID, holdings count,
filename, page/chunk count, model name, status, and duration. Search query text
is omitted from request/tool logs; diagnostic RAG events may include only a
short normalized preview.

## Configuration

Python services support:

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
ENVIRONMENT=development
```

`LOG_FORMAT=text` is available for local debugging. Docker keeps JSON logs on
stdout so they can later be collected by CloudWatch, OpenTelemetry, or another
observability system without changing application events.

## Viewing logs

```bash
docker compose logs -f
docker compose logs --since=10m
```

Browser events are visible in DevTools Console. Copy a response's
`X-Request-ID` and search container logs for the same value to reconstruct the
request path.
