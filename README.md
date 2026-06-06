# Apira

A dummy enterprise microservices system built for mentorship/learning purposes.

This repository is a hands-on learning project for exploring microservices architecture, API design, and full-stack development. It is not production software — it exists to teach patterns commonly found in enterprise systems.

## Services Overview

| Service | Description | Port |
|---------|-------------|------|
| **user-service** | Manages user accounts, authentication, and profile data | `8001` |
| **portfolio-service** | Manages investment portfolios, holdings, and performance data | `8002` |
| **frontend** | React web application that consumes the backend services | `3000` |

## Project Structure

```
apira/
├── user-service/                  # FastAPI user management service (+ Dockerfile)
├── portfolio-service/             # FastAPI portfolio management service (+ Dockerfile)
├── frontend/                      # React (Vite) web application (+ Dockerfile)
├── db/                            # SQL scripts to create + seed the database (run in pgAdmin)
│   ├── schema.sql
│   └── seed.sql
├── docker-compose.yml             # Runs all three services together
├── .env.example                   # Template for the DATABASE_URL connection string
├── apira.postman_collection.json  # Postman collection for the APIs
├── README.md
└── .gitignore
```

## Prerequisites

- **Python 3.9+**
- **Node.js 18+** and npm
- **PostgreSQL** database (e.g. AWS RDS) and **pgAdmin** to create the tables

## Database Setup

The services read from a PostgreSQL database with two tables (`users` and `portfolios`). They do **not** create the tables automatically — you create them once with the provided scripts.

1. In **pgAdmin**, connect to your database (local or AWS RDS) and open the Query Tool.
2. Run [db/schema.sql](db/schema.sql) to create the `users` and `portfolios` tables.
3. Run [db/seed.sql](db/seed.sql) to insert sample users and holdings.

Seeded logins: `alice` / `password` and `bob` / `password`.

Then tell the services how to connect by creating a `.env` file in the project root (copy from [.env.example](.env.example)):

```bash
cp .env.example .env
# edit .env and set DATABASE_URL to your database, e.g.:
# DATABASE_URL=postgresql+psycopg2://postgres:secret@your-rds-endpoint:5432/apira
```

Both services read the `DATABASE_URL` environment variable. Docker Compose automatically loads the `.env` file.

## Getting Started

### Option A: Docker Compose (recommended — one command)

Requires [Docker Desktop](https://www.docker.com/) (with the Compose plugin) installed and running.

```bash
docker compose up -d --build
```

This builds and starts all three services together in the background:

- Frontend → [http://localhost:3000](http://localhost:3000)
- User Service → [http://localhost:8001](http://localhost:8001)
- Portfolio Service → [http://localhost:8002](http://localhost:8002)

Common commands (run from the project root):

```bash
docker compose ps            # see what's running
docker compose logs -f       # follow live logs
docker compose down          # stop and remove the containers
docker compose up -d         # start again (no --build needed unless code/deps changed)
```

The `--build` flag is only needed the first time, or after you change code or dependencies.

### Option B: Run each service manually

Run the three commands below, each in its own terminal. The two Python services need `DATABASE_URL` set (see [Database Setup](#database-setup)).

#### User Service

```bash
cd user-service
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://postgres:secret@your-host:5432/apira
uvicorn main:app --reload --port 8001
```

#### Portfolio Service

```bash
cd portfolio-service
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://postgres:secret@your-host:5432/apira
uvicorn main:app --reload --port 8002
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs at [http://localhost:3000](http://localhost:3000).

## API Endpoints

All services have CORS enabled for all origins. Data is stored in PostgreSQL (see [Database Setup](#database-setup)).

### User Service (`http://localhost:8001`)

`POST /login` — validates the username/password against the `users` table.

Request body:

```json
{ "username": "alice", "password": "password" }
```

Success response (`200`):

```json
{ "success": true, "username": "alice", "user_id": 1 }
```

Invalid credentials return `401` with `{ "detail": "Invalid username or password" }`.

### Portfolio Service (`http://localhost:8002`)

`GET /portfolio?user_id=<id>` — returns the holdings belonging to that user from the `portfolios` table.

Example: `GET /portfolio?user_id=1`

Response:

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

## Testing the APIs

You have three easy options. Use **localhost** when running locally, or the **EC2 public IP** when testing the deployed services (see [AWS EC2 Deployment](#aws-ec2-deployment)).

- **Postman** — import `apira.postman_collection.json` (File → Import). Collection variables default to the EC2 deployment; switch them to `http://localhost:8001` / `http://localhost:8002` for local dev.
- **Swagger UI** — FastAPI auto-generates interactive docs. Local: [http://localhost:8001/docs](http://localhost:8001/docs) and [http://localhost:8002/docs](http://localhost:8002/docs). Deployed: `http://<EC2-IP>:8001/docs` and `:8002/docs`.
- **curl** (deployed example):

```bash
curl -X POST http://3.133.124.58:8001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password"}'

curl "http://3.133.124.58:8002/portfolio?user_id=1"
```

## How the Frontend Works

The React app (`frontend/src/App.jsx`) is a single component tree with two screens, toggled by a `user` object (`{ username, userId }`) held in React state (no localStorage, no tokens):

1. **Login screen** — username/password fields and a Login button that `POST`s to the user service. On success it stores the returned `username` and `user_id` in state, which swaps the view. Invalid credentials show an error message.
2. **Portfolio screen** — shows "Welcome, {username}", a "View My Portfolio" button that `GET`s `/portfolio?user_id=<id>` from the portfolio service and renders each holding as a line like "You own 150 shares of Apple Inc. (AAPL)", and a Logout button that clears the user and returns to the login screen.

## AWS EC2 Deployment

The two backend microservices are deployed on **AWS EC2** and connect to **AWS RDS PostgreSQL**. The React frontend is for **local development only** — it is not part of the EC2 deployment. Test deployed APIs with curl, Postman, or Swagger UI.

### Architecture

```
Laptop (curl, Postman, pgAdmin)
    │
    ├── SSH tunnel ──► EC2 (Docker: user-service :8001, portfolio-service :8002)
    │                      │
    │                      └── VPC ──► RDS PostgreSQL (users, portfolios tables)
    │
    └── HTTP :8001/:8002 ──► EC2 (API access, requires security group rules)
```

### Live endpoints (current deployment)

| Service | URL |
|---------|-----|
| User Service | `http://3.133.124.58:8001` |
| Portfolio Service | `http://3.133.124.58:8002` |
| Swagger docs | `http://3.133.124.58:8001/docs` and `:8002/docs` |

Test logins: `alice` / `password`, `bob` / `password`.

### Database setup (pgAdmin + RDS)

RDS is not reachable directly from a laptop. Connect pgAdmin through an **SSH tunnel** via the EC2 instance:

1. **pgAdmin → Register Server**
2. **Connection tab:** Host = RDS endpoint, Port `5432`, Database `postgres`, User `postgres`, SSL mode = Require
3. **SSH Tunnel tab:** Tunnel host = EC2 public IP, Port `22`, Username `ec2-user`, Identity file = your `.pem` key
4. Open **Query Tool** on the `postgres` database and run [db/schema.sql](db/schema.sql) then [db/seed.sql](db/seed.sql)

### EC2 security group inbound rules

The EC2 instance uses security group **`ec2-rds-1`**. Required inbound rules:

| Type | Port | Source | Purpose |
|------|------|--------|---------|
| SSH | 22 | Your IP (`x.x.x.x/32`) | SSH access + pgAdmin tunnel |
| Custom TCP | 8001 | Your IP | User service API |
| Custom TCP | 8002 | Your IP | Portfolio service API |

To add a rule: **VPC console → Security Groups → `ec2-rds-1` → Edit inbound rules → Add rule**. Use **Add rule** (do not edit existing referenced-group rules). Pick **My IP** for the source to auto-fill your current public IP.

### Running services on EC2

On the EC2 instance (`~/apira`):

```bash
# .env file (not committed) — DATABASE_URL points at RDS with ?sslmode=require
sudo docker compose up -d --build user-service portfolio-service
sudo docker compose ps
sudo docker compose logs -f
sudo docker compose down    # stop
```

`DATABASE_URL` format:

```
postgresql+psycopg2://postgres:PASSWORD@your-rds-endpoint.us-east-2.rds.amazonaws.com:5432/postgres?sslmode=require
```

URL-encode special characters in the password (e.g. `&` → `%26`).

### Updating the deployment

After pushing code changes to GitHub, copy the updated service folders to EC2 and rebuild:

```bash
# from your laptop — package and copy
tar czf /tmp/apira-deploy.tgz user-service portfolio-service docker-compose.yml
scp -i your-key.pem /tmp/apira-deploy.tgz ec2-user@3.133.124.58:/tmp/
ssh -i your-key.pem ec2-user@3.133.124.58 \
  "tar xzf /tmp/apira-deploy.tgz -C ~/apira && cd ~/apira && sudo docker compose up -d --build user-service portfolio-service"
```

### Local vs deployed

| | Local (`docker compose up`) | EC2 deployment |
|---|---|---|
| Needs `.env` with `DATABASE_URL` | Yes | Yes (on EC2 at `~/apira/.env`) |
| Can reach RDS from laptop | No (unless SSH tunnel) | N/A — EC2 reaches RDS inside VPC |
| API testing | `localhost:8001` / `localhost:8002` | `http://3.133.124.58:8001` / `:8002` |
