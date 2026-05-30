# Apira

A dummy enterprise microservices system built for mentorship/learning purposes.

This repository is a hands-on learning project for exploring microservices architecture, API design, and full-stack development. It is not production software — it exists to teach patterns commonly found in enterprise systems.

## Services Overview

| Service | Description | Port |
|---------|-------------|------|
| **user-service** | Manages user accounts, authentication, and profile data | `8001` |
| **portfolio-service** | Manages investment portfolios, holdings, and performance data | `8002` |
| **frontend** | React web application that consumes the backend services | `5173` |

## Project Structure

```
apira/
├── user-service/       # FastAPI user management service
├── portfolio-service/  # FastAPI portfolio management service
├── frontend/           # React (Vite) web application
├── README.md
└── .gitignore
```

## Prerequisites

- **Python 3.9+**
- **Node.js 18+** and npm

## Getting Started

### User Service

```bash
cd user-service
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### Portfolio Service

```bash
cd portfolio-service
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8002
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs at [http://localhost:5173](http://localhost:5173).

## Deployment (Future Phase)

This project will be deployed to **AWS EC2** in a later phase. Deployment configuration, infrastructure, and CI/CD pipelines are not yet included.

## License

This is a learning/mentorship project. Use it freely for educational purposes.
