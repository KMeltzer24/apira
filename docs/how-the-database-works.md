# How the Backend Connects to the Database

This doc explains how **user-service** and **portfolio-service** talk to the database — what library they use, how the connection is configured, and what happens on each API request.

**Short answer:** both services use **SQLAlchemy 2.x** (current, not outdated) to connect to **PostgreSQL on AWS RDS**. They do **not** use Microsoft SQL Server.

---

## PostgreSQL, not SQL Server

Apira stores data in **AWS RDS PostgreSQL** (port 5432). When people say "SQL server" they sometimes mean any database; in this project that means **PostgreSQL**.

| Term | What Apira uses |
|------|-----------------|
| Database engine | **PostgreSQL** (RDS) |
| Wire protocol / port | PostgreSQL on **5432** |
| Python driver | **psycopg2** (`psycopg2-binary` in `requirements.txt`) |
| ORM / query layer | **SQLAlchemy 2.0** |

RDS is in a private VPC. Only EC2 can reach it — not your browser, not the frontend, not the internet directly.

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
postgresql+psycopg2://<user>:<password>@<rds-host>:5432/<dbname>
```

That value is set once on EC2 as the **`DATABASE_URL`** environment variable (see `docker-compose.backend.yml`). Both containers receive the same URL.

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
| `create_engine(DATABASE_URL)` | Opens a connection pool to RDS |
| `pool_pre_ping=True` | Checks connections before use (helps after RDS idle timeouts) |
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

The app does **not** run migrations or `CREATE TABLE` on startup. Tables and seed data (`alice`, `bob`, holdings) were created manually in RDS (via pgAdmin over an SSH tunnel). See [deploy-ec2.md](deploy-ec2.md).

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
PostgreSQL (RDS) — SELECT from users
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
PostgreSQL (RDS) — SELECT from portfolios
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
user-service or portfolio-service (EC2 Docker, ports 8001 / 8002)
  │  SQLAlchemy Session + psycopg2
  ▼
AWS RDS PostgreSQL (private VPC, port 5432)
```

MCP and the agent **never** connect to RDS directly. They call the FastAPI HTTP APIs; only the two backend services open database connections.

---

## Configuration checklist

| Setting | Where | Example |
|---------|-------|---------|
| `DATABASE_URL` | EC2 `~/apira/.env` or shell env | `postgresql+psycopg2://apira:****@mydb.xxxx.rds.amazonaws.com:5432/apira` |
| Passed to containers | `docker-compose.backend.yml` | `environment: - DATABASE_URL=${DATABASE_URL}` |
| RDS security group | AWS console | Allow **5432** from EC2 security group |

---

## Further reading

| Doc | Content |
|-----|---------|
| [deploy-ec2.md](deploy-ec2.md) | RDS setup, seed data, EC2 deploy |
| [architecture.md](architecture.md) | Full system diagram including RDS |
| [SQLAlchemy 2.0 docs](https://docs.sqlalchemy.org/en/20/) | Official ORM / Core reference |
