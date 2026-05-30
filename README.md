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
├── docker-compose.yml             # Runs all three services together
├── apira.postman_collection.json  # Postman collection for the APIs
├── README.md
└── .gitignore
```

## Prerequisites

- **Python 3.9+**
- **Node.js 18+** and npm

## Getting Started

### Option A: Docker Compose (recommended — one command)

Requires [Docker](https://www.docker.com/) with the Compose plugin.

```bash
docker compose up --build
```

This builds and starts all three services together:

- Frontend → [http://localhost:3000](http://localhost:3000)
- User Service → [http://localhost:8001](http://localhost:8001)
- Portfolio Service → [http://localhost:8002](http://localhost:8002)

Stop everything with `Ctrl+C`, or remove the containers with `docker compose down`.

### Option B: Run each service manually

Run the three commands below, each in its own terminal.

#### User Service

```bash
cd user-service
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

#### Portfolio Service

```bash
cd portfolio-service
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
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

All services have CORS enabled for all origins. There is no database — every value is hardcoded.

### User Service (`http://localhost:8001`)

`POST /login` — accepts any credentials, always succeeds.

Request body:

```json
{ "username": "alice", "password": "anything" }
```

Response:

```json
{ "success": true, "username": "alice" }
```

### Portfolio Service (`http://localhost:8002`)

`GET /portfolio` — returns a fixed list of stock holdings.

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

The React app (`frontend/src/App.jsx`) is a single component tree with two screens, toggled by a single `username` value in React state (no localStorage, no tokens):

1. **Login screen** — username/password fields and a Login button that `POST`s to the user service. On success it stores the returned username in state, which swaps the view.
2. **Portfolio screen** — shows "Welcome, {username}", a "View My Portfolio" button that `GET`s from the portfolio service and renders each holding as a line like "You own 150 shares of Apple Inc. (AAPL)", and a Logout button that clears the username and returns to the login screen.

## Deployment (Future Phase)

This project will be deployed to **AWS EC2** in a later phase. Deployment configuration, infrastructure, and CI/CD pipelines are not yet included.

## License

This is a learning/mentorship project. Use it freely for educational purposes.
