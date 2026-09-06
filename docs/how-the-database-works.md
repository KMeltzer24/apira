# How the Backend Connects to the Database

This doc explains how **user-service** and **portfolio-service** talk to the database — what library they use, how the connection is configured, and what happens on each API request.

**Short answer:** both services use **SQLAlchemy 2.x** to connect to **PostgreSQL** via local Docker Compose (`docs/run-locally.md`). They do **not** use Microsoft SQL Server.

---

## PostgreSQL, not SQL Server

Apira stores data in **PostgreSQL** (port 5432) on your Mac (`docker-compose.local.yml`). When people say "SQL server" they sometimes mean any database; in this project that means **PostgreSQL**.

| Term | What Apira uses |
|------|-----------------|
| Database engine | **PostgreSQL** (pgvector image locally) |
| Wire protocol / port | PostgreSQL on **5432** |
| Python driver | **psycopg2** (`psycopg2-binary` in `requirements.txt`) |
| ORM / query layer | **SQLAlchemy 2.0** |

Services reach Postgres at `localhost:5432` from the Mac, or `host.docker.internal:5432` / the Compose service name from containers.

---

## Stack in each service

Both `user-service` and `portfolio-service` share the same database pattern:

| File | Role |
|------|------|
| `db.py` | Reads `DATABASE_URL`, creates SQLAlchemy engine + session factory |
| `models.py` | Maps Python classes to SQL tables (`users`, `portfolios`) |
| `main.py` | FastAPI routes; opens a DB session per request and runs queries |

Dependencies (`requirements.txt` in each service):

```
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
```

SQLAlchemy talks to PostgreSQL through the **psycopg2** driver. The connection string uses SQLAlchemy's URL format:

```
postgresql+psycopg2://apira:apira@postgres:5432/apira
```

That value is set as **`DATABASE_URL`** in `docker-compose.local.yml`. Both backend containers receive the same URL.

---

## Is SQLAlchemy outdated?

**No.** SQLAlchemy is the standard Python database toolkit and is actively maintained. This project uses **SQLAlchemy 2.0** style, which is the current recommended API:

| Import / pattern | Status |
|------------------|--------|
| `from sqlalchemy import create_engine, select` | Current (2.x) |
| `from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session` | Current (2.x) |
| `db.execute(select(User).where(...))` | Current (2.x) — replaces old `session.query(User)` |
| `DeclarativeBase` | Current — replaces old `declarative_base()` |

You will **not** see legacy patterns like `session.query(User).filter_by(...)` in this codebase. The imports in `main.py` and `models.py` are intentional and up to date.

---

## Connection setup (`db.py`)

Both services use the same `db.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

What each piece does:

| Piece | Purpose |
|-------|---------|
| `create_engine(DATABASE_URL)` | Opens a connection pool to Postgres |
| `pool_pre_ping=True` | Checks connections before use |
| `sessionmaker` | Factory that creates one **Session** per request |
| `get_db()` | FastAPI dependency — yields a session, then closes it |

If `DATABASE_URL` is missing, the service fails at startup with a clear error.

---

## Table models (`models.py`)

SQLAlchemy maps rows to Python objects:

**user-service** — `User` → `users` table:

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
```

**portfolio-service** — `Portfolio` → `portfolios` table:

```python
class Portfolio(Base):
    __tablename__ = "portfolios"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    ticker: Mapped[str]
    company: Mapped[str]
    shares: Mapped[int]
```

The app does **not** run migrations or `CREATE TABLE` on startup. Local Compose applies `sql/local-seed.sql` on **first** Postgres volume create (tables + `alice` / `bob`). See [run-locally.md](run-locally.md).

---

## Request flow

### user-service — `POST /login`

```
Client
  │  POST /login { username, password }
  ▼
FastAPI (main.py)
  │  db: Session = Depends(get_db)   ← opens SQLAlchemy session
  ▼
db.execute(select(User).where(User.username == ...))
  ▼
PostgreSQL — SELECT from users
  ▼
Return { success, username, user_id } or 401
  ▼
get_db() closes session
```

### portfolio-service — `GET /portfolio?user_id=`

```
Client
  │  GET /portfolio?user_id=1
  ▼
FastAPI (main.py)
  │  db: Session = Depends(get_db)
  ▼
db.execute(select(Portfolio).where(Portfolio.user_id == ...))
  ▼
PostgreSQL — SELECT from portfolios
  ▼
Return { holdings: [...] }
  ▼
get_db() closes session
```

Neither service writes to the database in normal operation — login only **reads** `users`; portfolio only **reads** `portfolios`.

---

## End-to-end path (who touches the DB)

```
Browser / MCP / Agent
  │
  ▼
user-service or portfolio-service (Docker, ports 8001 / 8002)
  │  SQLAlchemy Session + psycopg2
  ▼
PostgreSQL (local Compose, port 5432)
```

MCP and the agent **never** connect to Postgres directly for user/portfolio data — they call the FastAPI HTTP APIs. **Exception:** [apira-rag](https://github.com/KMeltzer24/apira-rag) connects to the same Postgres for the `research_chunks` pgvector table used by `searchVectorDB`.

---

## pgvector table (apira-rag)

Stock research embeddings live in the **same Postgres database**, written/read by **apira-rag** (not user-service or portfolio-service):

| Table | Used by | Purpose |
|-------|---------|---------|
| `users` | user-service | Login |
| `portfolios` | portfolio-service | Holdings |
| `research_chunks` | apira-rag | RAG embeddings (`vector(768)`) |

Schema is applied by apira-rag (`rag/schema.py` / ingest scripts). Local folder search does not need embeddings.

---

## Configuration checklist

| Setting | Where | Example |
|---------|-------|---------|
| `DATABASE_URL` | `docker-compose.local.yml` | `postgresql+psycopg2://apira:apira@postgres:5432/apira` |
| RAG `DATABASE_URL` | `apira-rag` `.env` | `postgresql+psycopg2://apira:apira@host.docker.internal:5432/apira` |

---

## Further reading

| Doc | Content |
|-----|---------|
| [run-locally.md](run-locally.md) | Local Postgres seed + full stack |
| [architecture.md](architecture.md) | Full system diagram |
| [apira-rag: vector-search-params.md](https://github.com/KMeltzer24/apira-rag/blob/main/docs/vector-search-params.md) | Similarity / HNSW params |
| [SQLAlchemy 2.0 docs](https://docs.sqlalchemy.org/en/20/) | Official ORM / Core reference |
