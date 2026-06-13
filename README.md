# Apira

A dummy enterprise microservices system built for mentorship/learning purposes.

Two FastAPI backend services and an MCP server on **AWS EC2**, backed by **AWS RDS PostgreSQL**.

**Stack:** Python, FastAPI, PostgreSQL (RDS), Postman.

**Frontend (separate repo):** [apira-frontend](https://github.com/KMeltzer24/apira-frontend)

## Services

| Service | Port | Description |
|---------|------|-------------|
| **user-service** | `8001` | `POST /login` — validates credentials against the `users` table |
| **portfolio-service** | `8002` | `GET /portfolio?user_id=<id>` — returns per-user holdings from the `portfolios` table |
| **mcp-server** | `8000` | MCP over HTTP at `/mcp` — tools: `login`, `get_portfolio(user_id)` |

Demo logins (seed data): `alice` / `password`, `bob` / `password`.

## AWS security group

The EC2 security group must allow inbound **TCP 8000**, **8001**, and **8002** from your laptop IP (same pattern as SSH). Port 8000 is required for remote MCP clients to reach the MCP server.

## Project Structure

```
apira/
├── user-service/
├── portfolio-service/
├── mcp-server/
├── docker-compose.backend.yml     # EC2 deployment
├── docs/deploy-ec2.md
├── apira.postman_collection.json
└── README.md
```

## Architecture

```
Client (Postman, curl, MCP) → EC2 (user-service, portfolio-service, mcp-server) → RDS PostgreSQL
```

## MCP Server

Streamable HTTP endpoint: `http://<EC2_PUBLIC_IP>:8000/mcp`

| Tool | Wraps |
|------|--------|
| `login(username, password)` | `POST /login` on user-service |
| `get_portfolio(user_id)` | `GET /portfolio?user_id=` on portfolio-service |

No authentication on the MCP endpoint (learning project). MCP client configuration is separate from this repo.

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
