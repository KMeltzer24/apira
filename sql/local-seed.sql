-- First-boot seed for local Docker Postgres (docker-entrypoint-initdb.d).
-- Demo logins (bcrypt): alice / password, bob / password.
-- Re-create the volume after changing this file: docker compose -f docker-compose.local.yml down -v

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    password VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    ticker VARCHAR NOT NULL,
    company VARCHAR NOT NULL,
    shares INTEGER NOT NULL
);

INSERT INTO users (id, username, password) VALUES
    (1, 'alice', '$2b$12$1Wae9KqBggLlzYE1tEr5oO4Y7jtlekYGbhbdJ9d/GcYisJenp8dnC'),
    (2, 'bob', '$2b$12$1Wae9KqBggLlzYE1tEr5oO4Y7jtlekYGbhbdJ9d/GcYisJenp8dnC')
ON CONFLICT (username) DO NOTHING;

SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

INSERT INTO portfolios (user_id, ticker, company, shares) VALUES
    (1, 'AAPL', 'Apple Inc.', 150),
    (1, 'MSFT', 'Microsoft Corp.', 80),
    (1, 'GOOGL', 'Alphabet Inc.', 25),
    (1, 'AMZN', 'Amazon.com Inc.', 40),
    (1, 'TSLA', 'Tesla Inc.', 60),
    (2, 'NVDA', 'NVIDIA Corp.', 40),
    (2, 'META', 'Meta Platforms Inc.', 30),
    (2, 'JPM', 'JPMorgan Chase & Co.', 100),
    (2, 'KO', 'The Coca-Cola Company', 200);

CREATE TABLE IF NOT EXISTS recommendations (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
