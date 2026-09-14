-- Apply on an existing local Postgres volume (init scripts only run on first boot).
CREATE TABLE IF NOT EXISTS recommendations (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
