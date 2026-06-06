-- Apira seed data
-- Run this in pgAdmin AFTER schema.sql.
-- Passwords are plaintext for this demo only (not for production).

INSERT INTO users (username, password) VALUES
    ('alice', 'password'),
    ('bob',   'password');

-- Alice's holdings (matches the original hardcoded demo list).
INSERT INTO portfolios (user_id, ticker, company, shares) VALUES
    ((SELECT id FROM users WHERE username = 'alice'), 'AAPL',  'Apple Inc.',      150),
    ((SELECT id FROM users WHERE username = 'alice'), 'MSFT',  'Microsoft Corp.',  80),
    ((SELECT id FROM users WHERE username = 'alice'), 'GOOGL', 'Alphabet Inc.',    25),
    ((SELECT id FROM users WHERE username = 'alice'), 'AMZN',  'Amazon.com Inc.',  40),
    ((SELECT id FROM users WHERE username = 'alice'), 'TSLA',  'Tesla Inc.',       60);

-- Bob has a smaller, different portfolio to show per-user data.
INSERT INTO portfolios (user_id, ticker, company, shares) VALUES
    ((SELECT id FROM users WHERE username = 'bob'), 'NVDA', 'NVIDIA Corp.',    30),
    ((SELECT id FROM users WHERE username = 'bob'), 'AMD',  'Advanced Micro Devices Inc.', 100);
