-- Migration 003: Add photo_url column to candidates table
-- Run this against your database after backing it up.
-- Example (Postgres):
-- psql "postgresql://user:pass@host:port/dbname" -f 003_add_photo_url_to_candidates.sql

ALTER TABLE candidates ADD COLUMN IF NOT EXISTS photo_url TEXT DEFAULT NULL;
