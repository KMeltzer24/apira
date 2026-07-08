# Apira

A dummy enterprise microservices system built for mentorship/learning purposes.

Two FastAPI backend services on **AWS EC2**, backed by **AWS RDS PostgreSQL**.

**Stack:** Python, FastAPI, PostgreSQL (RDS), Postman.

**Frontend (separate repo):** [apira-frontend](https://github.com/KMeltzer24/apira-frontend)

**MCP server (separate repo):** [apira-mcp](https://github.com/KMeltzer24/apira-mcp)

**Agent (separate repo):** [apira-agent](https://github.com/KMeltzer24/apira-agent)

## Services

| Service | Port | Description |
|---------|------|-------------|
| **user-service** | `8001` | `POST /login` — validates credentials against the `users` table |
| **portfolio-service** | `8002` | `GET /portfolio?user_id=<id>` — returns per-user holdings from the `portfolios` table |

Demo logins (seed data): `alice` / `password`, `bob` / `password`.

The MCP server (port `8000`) lives in [apira-mcp](https://github.com/KMeltzer24/apira-mcp) and wraps the two APIs above.

## AWS security group

The EC2 security group must allow inbound **TCP 8000**, **8001**, **8002**, and **8100** from your laptop IP (same pattern as SSH). 8000 is for MCP clients; 8100 is the agent API.

## Project Structure

```
apira/
├── user-service/
├── portfolio-service/
├── docker-compose.backend.yml     # EC2 deployment
├── docs/architecture.md
├── docs/deploy-ec2.md
├── apira.postman_collection.json
└── README.md
```

## Architecture

See **[docs/architecture.md](docs/architecture.md)** for the full system diagram (frontend, agent, MCP, backend, RDS, Gemini).

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

## Deployment

Backend services are deployed to EC2 with Docker. See **[docs/deploy-ec2.md](docs/deploy-ec2.md)** for the full deploy, update, and verification guide.

MCP server deployment: **[apira-mcp](https://github.com/KMeltzer24/apira-mcp)**.
