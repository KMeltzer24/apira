-- Apira database schema
-- Run this in pgAdmin (Query Tool) against your target database.
-- Creates the two tables the microservices read from.

DROP TABLE IF EXISTS portfolios;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id       SERIAL PRIMARY KEY,
    username VARCHAR(50)  UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL
);

CREATE TABLE portfolios (
    id      SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    ticker  VARCHAR(10)  NOT NULL,
    company VARCHAR(100) NOT NULL,
    shares  INTEGER NOT NULL
);
