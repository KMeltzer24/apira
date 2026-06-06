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

You have three easy options:

- **Postman** — import `apira.postman_collection.json` (File → Import). It includes both requests with the service URLs preset as collection variables.
- **Swagger UI** — FastAPI auto-generates interactive docs at [http://localhost:8001/docs](http://localhost:8001/docs) and [http://localhost:8002/docs](http://localhost:8002/docs). Click "Try it out" to send requests from the browser.
- **curl**:

```bash
curl -X POST http://localhost:8001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"anything"}'

curl http://localhost:8002/portfolio
```

## How the Frontend Works

The React app (`frontend/src/App.jsx`) is a single component tree with two screens, toggled by a `user` object (`{ username, userId }`) held in React state (no localStorage, no tokens):

1. **Login screen** — username/password fields and a Login button that `POST`s to the user service. On success it stores the returned `username` and `user_id` in state, which swaps the view. Invalid credentials show an error message.
2. **Portfolio screen** — shows "Welcome, {username}", a "View My Portfolio" button that `GET`s `/portfolio?user_id=<id>` from the portfolio service and renders each holding as a line like "You own 150 shares of Apple Inc. (AAPL)", and a Logout button that clears the user and returns to the login screen.

## Deployment (Future Phase)

This project will be deployed to **AWS EC2** in a later phase. Deployment configuration, infrastructure, and CI/CD pipelines are not yet included.
