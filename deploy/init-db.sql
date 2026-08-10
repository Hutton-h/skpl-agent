-- SKPL Agent Database Initialization
-- Creates extensions and initial schema for PostgreSQL
-- Note: This is a fallback for PostgreSQL container init.
-- The primary schema is managed by Alembic migrations (0001 -> 0002 -> 0003).

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set default configuration
ALTER DATABASE skpl SET timezone TO 'UTC';

-- ── SKPL: Users table (matches alembic 0003_auth_org.py) ────────────────────
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE,
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- ── SKPL: Organizations table (matches alembic 0003_auth_org.py) ────────────
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    owner_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ── SKPL: Organization members (matches alembic 0003_auth_org.py) ───────────
CREATE TABLE IF NOT EXISTS org_members (
    id VARCHAR(36) PRIMARY KEY,
    org_id VARCHAR(36) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(org_id, user_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);
CREATE INDEX IF NOT EXISTS ix_organizations_name ON organizations(name);
CREATE INDEX IF NOT EXISTS ix_organizations_owner_id ON organizations(owner_id);
CREATE INDEX IF NOT EXISTS ix_org_members_user_id ON org_members(user_id);
CREATE INDEX IF NOT EXISTS ix_org_members_org_id ON org_members(org_id);