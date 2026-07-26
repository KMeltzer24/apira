# Deploy Backend to EC2

This doc explains how the Apira backends got onto EC2 and how to update them after code changes.

**What runs on EC2:** `user-service` (8001) and `portfolio-service` (8002) in Docker.

**Separate repos (not in this tarball):**

- Frontend — [apira-frontend](https://github.com/KMeltzer24/apira-frontend) runs on your Mac
- Backend MCP — [apira-mcp](https://github.com/KMeltzer24/apira-mcp) deploys to EC2 separately (port 8000)
- Research MCP — [apira-rag](https://github.com/KMeltzer24/apira-rag) deploys to EC2 separately (host port 8200)
- Agent — [apira-agent](https://github.com/KMeltzer24/apira-agent) deploys to EC2 separately (port 8100, uses the Gemini API)

```
Postman / curl / frontend / MCP clients  →  EC2 (Docker)  →  RDS PostgreSQL
```

---

## What we set up once

These steps were done when the project was first deployed. You should not need to repeat them unless you rebuild the AWS environment.

### 1. AWS infrastructure

- **EC2** — Amazon Linux, SSH user `ec2-user`
- **RDS** — PostgreSQL in the same VPC (not public from the internet)
- **Security groups**
  - EC2: inbound SSH (22), TCP 8000, TCP 8001, TCP 8002, TCP 8100, TCP 8300
    (log-service) from your laptop IP
  - RDS: inbound PostgreSQL (5432) from the EC2 security group

`apira-rag` publishes host port 8200 so the agent container can reach it through `host.docker.internal`. No public inbound rule for 8200 is required.

### 2. Software on EC2

Docker and Docker Compose were installed on the instance.

### 3. App directory on EC2

Backend code lives in:

```bash
~/apira/
```

MCP server code lives in:

```bash
~/apira-mcp/
```

Research service code lives in:

```bash
~/apira-rag/
```

### 4. Database

Tables (`users`, `portfolios`) and seed data were created in RDS using pgAdmin (via SSH tunnel). The app does not create tables on startup.

Both services connect via **SQLAlchemy 2.x** + **psycopg2** using the `DATABASE_URL` env var. See **[how-the-database-works.md](how-the-database-works.md)** for the full connection and query flow.

---

## How the first deploy worked

From your Mac, in the `apira` repo root:

**Step 1 — Package the backend files**

```bash
tar czf /tmp/apira-deploy.tgz \
  user-service portfolio-service log-service observability \
  docker-compose.backend.yml docker-compose.observability.yml \
  .env.observability.example
```

**Step 2 — Copy to EC2**

```bash
scp -i my-ec2-key.pem /tmp/apira-deploy.tgz ec2-user@<EC2_PUBLIC_IP>:/tmp/
```

**Step 3 — Extract and start Docker on EC2**

```bash
ssh -i my-ec2-key.pem ec2-user@<EC2_PUBLIC_IP> \
  "mkdir -p ~/apira && \
   tar xzf /tmp/apira-deploy.tgz -C ~/apira && \
   cd ~/apira && \
   sudo docker compose -f docker-compose.backend.yml up -d --build"
```

This builds two Docker images and starts two containers. Docker reads `DATABASE_URL` from `~/apira/.env`.

**Step 3b — Observability (Grafana Cloud)**

Create `~/apira/.env.observability` from `.env.observability.example` with your
Loki URL / user / API key, then:

```bash
cd ~/apira
sudo docker compose -f docker-compose.observability.yml \
  --env-file .env.observability up -d --build
```

Full details: [grafana-cloud.md](grafana-cloud.md).

**Step 4 — Deploy MCP server**

Follow the deploy steps in [apira-mcp](https://github.com/KMeltzer24/apira-mcp). The MCP container calls the backend via host ports 8001 and 8002.

**Step 5 — Deploy research service**

Follow the deploy steps in [apira-rag](https://github.com/KMeltzer24/apira-rag). It uses the existing RDS `research_chunks` table, so splitting the repositories does not require a database migration.

---

## How to update after code changes

Use the **same three steps** whenever you change Python code, `requirements.txt`, or Dockerfiles on your Mac:

```bash
# 1. Package
tar czf /tmp/apira-deploy.tgz \
  user-service portfolio-service log-service observability \
  docker-compose.backend.yml docker-compose.observability.yml \
  .env.observability.example

# 2. Copy
scp -i my-ec2-key.pem /tmp/apira-deploy.tgz ec2-user@<EC2_PUBLIC_IP>:/tmp/

# 3. Extract and rebuild on EC2
ssh -i my-ec2-key.pem ec2-user@<EC2_PUBLIC_IP> \
  "tar xzf /tmp/apira-deploy.tgz -C ~/apira && \
   cd ~/apira && \
   sudo docker compose -f docker-compose.backend.yml up -d --build && \
   sudo docker compose -f docker-compose.observability.yml \
     --env-file .env.observability up -d --build"
```

| Situation | What to do |
|-----------|------------|
| Code or dependency changed | Use `--build` (as above) |
| Restart only, no code changes | Drop `--build`: `up -d` |
| Changed RDS password | Edit `~/apira/.env` on EC2 directly (not via tarball) |
| Changed Grafana credentials | Edit `~/apira/.env.observability` on EC2 (not via tarball) |
| MCP server changed | Redeploy from [apira-mcp](https://github.com/KMeltzer24/apira-mcp) |
| Research pipeline changed | Redeploy from [apira-rag](https://github.com/KMeltzer24/apira-rag) |

The tarball never overwrites `~/apira/.env` or `~/apira/.env.observability`.

---

## Verify it works

**APIs from your Mac:**

```bash
curl -X POST http://<EC2_PUBLIC_IP>:8001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password"}'

curl "http://<EC2_PUBLIC_IP>:8002/portfolio?user_id=1"
```

Both should return HTTP 200 and JSON.

**MCP endpoint from your Mac:**

```bash
curl -i http://<EC2_PUBLIC_IP>:8000/mcp
```

Should connect (not time out). Deploy and verify MCP via [apira-mcp](https://github.com/KMeltzer24/apira-mcp).

**On EC2 (SSH in first):**

```bash
cd ~/apira
sudo docker compose -f docker-compose.backend.yml ps

cd ~/apira-mcp
sudo docker compose ps

cd ~/apira-rag
sudo docker compose ps
```

You should see backend containers and both MCP containers **Up**.

### Follow a request through logs

Prefer Grafana Explore (LogQL) once observability is up — see
[grafana-cloud.md](grafana-cloud.md). Application events are still JSON on
container stdout. Start with the `X-Request-ID` response header, then search:

```bash
cd ~/apira-agent && sudo docker compose logs --since=10m
cd ~/apira-mcp && sudo docker compose logs --since=10m
cd ~/apira-rag && sudo docker compose logs --since=10m
cd ~/apira && sudo docker compose -f docker-compose.backend.yml logs --since=10m
```

Set `LOG_LEVEL=DEBUG` only while diagnosing a problem, then return it to
`INFO`. See [how-logging-works.md](how-logging-works.md),
[logging.md](logging.md), and the demo steps in
[demo-logging.md](demo-logging.md).

---

## Troubleshooting

| Problem | Likely fix |
|---------|------------|
| Timeout from Mac | EC2 stopped, or your public IP changed — update security group rules |
| Works on EC2, not from Mac | Open inbound ports 8000, 8001, and 8002 for your current IP |
| Container keeps crashing | Check logs; confirm `~/apira/.env` exists and RDS is running |
| MCP up but tools fail | Confirm user-service and portfolio-service containers are running |

**Restart backend containers:**

```bash
cd ~/apira
sudo docker compose -f docker-compose.backend.yml up -d
```

**Stop backend containers:**

```bash
sudo docker compose -f docker-compose.backend.yml down
```

Replace `<EC2_PUBLIC_IP>` with your value from the AWS console.
