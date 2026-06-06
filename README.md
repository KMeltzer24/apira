# Apira

A dummy enterprise microservices system built for mentorship/learning purposes.

Two FastAPI backend services on **AWS EC2**, backed by **AWS RDS PostgreSQL**.

**Stack:** Python, FastAPI, PostgreSQL (RDS), Postman. React frontend for local dev only.

## Services

| Service | Port | Description |
|---------|------|-------------|
| **user-service** | `8001` | `POST /login` — validates credentials against the `users` table |
| **portfolio-service** | `8002` | `GET /portfolio?user_id=<id>` — returns per-user holdings from the `portfolios` table |

Demo logins (seed data): `alice` / `password`, `bob` / `password`.

## Project Structure

```
apira/
├── user-service/
├── portfolio-service/
├── frontend/                      # local dev only, not deployed
├── docker-compose.yml
├── apira.postman_collection.json
└── README.md
```

## Architecture

```
Client (Postman, curl) → EC2 (user-service, portfolio-service) → RDS PostgreSQL
```

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
