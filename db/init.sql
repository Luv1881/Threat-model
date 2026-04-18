-- VaultNote Database Schema
-- Run automatically by PostgreSQL on first container start

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,     -- bcrypt hash
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Notes table
CREATE TABLE IF NOT EXISTS notes (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255) NOT NULL DEFAULT 'Untitled',
    content     TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- File attachments table
CREATE TABLE IF NOT EXISTS attachments (
    id          SERIAL PRIMARY KEY,
    note_id     INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename    VARCHAR(255) NOT NULL,
    object_key  VARCHAR(512) NOT NULL,   -- MinIO object key
    size_bytes  BIGINT,
    mime_type   VARCHAR(128),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Seed a demo user (password: demo1234)
-- bcrypt hash of "demo1234" with 10 rounds
INSERT INTO users (email, password) VALUES
    ('demo@vaultnote.local', '$2b$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lh7y')
ON CONFLICT DO NOTHING;
