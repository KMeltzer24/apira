# Grafana Cloud Logging

Apira ships structured JSON logs to **Grafana Cloud (Loki)** so one
`request_id` / `user_id` can be queried across frontend, agent, MCP, RAG, and
backend APIs without building a custom log warehouse.

**Free forever tier** (as of this writing) includes enough logs for demos
(~50 GB/month ingest, short retention). Create an account at
[grafana.com](https://grafana.com/auth/sign-up/create-user/).

## Architecture

```text
Browser (apira-frontend)
  │  POST /v1/logs  (batched structured JSON)
  ▼
log-service (:8300) ──► local file /var/log/apira/frontend.jsonl
  │
  └──────────────────► Grafana Cloud Loki

Docker containers (EC2 or local Compose)
  │  stdout JSON (user, portfolio, mcp, rag, agent, log-service)
  ▼
Grafana Alloy ──────────────────► Grafana Cloud Loki

You ──► Grafana Explore (LogQL) by request_id / user_id / service
```

Credentials stay in `.env.observability` (EC2 or your Mac). The browser never receives the Loki API key.

| Piece | Role |
|-------|------|
| `log-service` | Accepts frontend events, appends a local JSONL file, pushes to Loki |
| `Grafana Alloy` | Tails Docker container logs and pushes to Loki |
| Grafana Cloud | Query UI (Explore) + retention |

Compose file: [`docker-compose.observability.yml`](../docker-compose.observability.yml)  
Alloy config: [`observability/config.alloy`](../observability/config.alloy)

## One-time Grafana Cloud setup

1. Sign up for Grafana Cloud Free and open your stack.
2. Go to **Connections → Add new connection → Hosted logs** (or Alloy).
3. Copy:
   - **Loki push URL** ending in `/loki/api/v1/push`
   - **User** (numeric instance id)
   - Create a **Cloud Access Policy** token with `logs:write` (and usually
     `logs:read` for Explore in the same stack)
4. Create `.env.observability` from
   [`.env.observability.example`](../.env.observability.example)
   (on EC2 at `~/apira/`, or in this repo on your Mac).

## Local Mac

See **[run-locally.md](run-locally.md)**. Same Loki credentials, `docker-compose.local.yml`.

## Deploy on EC2

Security group: allow inbound **TCP 8300** from your laptop (frontend on Mac
POSTs to log-service). Alloy does not need a public port.

```bash
# From Mac — include observability files in the deploy tarball
cd ~/development/apira
tar czf /tmp/apira-deploy.tgz \
  user-service portfolio-service log-service observability \
  docker-compose.backend.yml docker-compose.observability.yml \
  .env.observability.example

scp -i my-ec2-key.pem /tmp/apira-deploy.tgz ec2-user@<EC2_IP>:/tmp/
```

On EC2:

```bash
cd ~
mkdir -p apira && tar xzf /tmp/apira-deploy.tgz -C apira
cd ~/apira
cp .env.observability.example .env.observability
# edit .env.observability with real GRAFANA_LOKI_* values

sudo docker compose -f docker-compose.observability.yml \
  --env-file .env.observability up -d --build
```

Check:

```bash
curl -s http://127.0.0.1:8300/health
sudo docker compose -f docker-compose.observability.yml \
  --env-file .env.observability logs --since=5m
```

## Frontend wiring

In `apira-frontend` `.env` (Mac):

```bash
VITE_LOG_SERVICE_URL=http://<EC2_PUBLIC_IP>:8300
```

Rebuild/restart the frontend container so Vite picks up the env var. Browser
events still print to DevTools; they are also batched to log-service.

## Query examples (Grafana Explore → Loki)

```logql
{job="docker"} |= "request_id"
```

```logql
{job="apira"} | json | request_id = "<paste-uuid>"
```

```logql
{job=~"docker|apira"} | json | user_id = "1"
```

```logql
{service="apira-agent"} | json | event = "chat.started"
```

Same `request_id` should appear for agent → mcp/rag → user/portfolio on one
Agent Chat or Recommender call. Frontend lines use `job="apira"` via
log-service; container lines use `job="docker"` (plus extracted `service`
labels when the line is JSON).

## Local files on EC2

- Frontend batches: Docker volume `apira-logs` → `/var/log/apira/frontend.jsonl`
  inside the log-service container.
- Backend/agent/MCP/RAG: Docker’s `json-file` log driver already stores
  container stdout under `/var/lib/docker/containers/…` on the host; Alloy
  reads those and ships them to Grafana.

Inspect frontend file:

```bash
sudo docker compose -f docker-compose.observability.yml \
  --env-file .env.observability exec log-service \
  tail -n 20 /var/log/apira/frontend.jsonl
```

## Memory note

The EC2 instance is small. Alloy (~192 MB limit) and log-service (~128 MB
limit) are capped in compose. If the host OOMs during image builds, reboot and
rebuild one compose project at a time; leave observability up once built.

## Related docs

- [logging.md](logging.md) — event schema / redaction
- [how-logging-works.md](how-logging-works.md) — narrative + correlation
- [how-logging-works.md](how-logging-works.md) — correlation narrative + Alice lookbacks
