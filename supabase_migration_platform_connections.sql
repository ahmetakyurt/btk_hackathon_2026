-- Migration: platform_connections table
-- Run in Supabase Studio → SQL Editor
-- Created: 2026-05-12

CREATE TABLE IF NOT EXISTS platform_connections (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform_id     INTEGER NOT NULL REFERENCES platforms(id) ON DELETE CASCADE,
    seller_id       TEXT,
    api_key         TEXT,
    status          TEXT NOT NULL DEFAULT 'connected',
    connected_at    TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    CONSTRAINT uq_user_platform_conn UNIQUE (user_id, platform_id)
);

CREATE INDEX IF NOT EXISTS ix_platform_connections_user_id
    ON platform_connections (user_id);

-- Enable RLS (backend superuser bypasses; anon API key is blocked)
ALTER TABLE platform_connections ENABLE ROW LEVEL SECURITY;
