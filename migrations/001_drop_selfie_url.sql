-- Migration 001: Drop selfie_url column from verification_logs
-- Run this against your database after backing it up.
-- Example (Postgres):
-- psql "postgresql://user:pass@host:port/dbname" -f 001_drop_selfie_url.sql

ALTER TABLE IF EXISTS verification_logs DROP COLUMN IF EXISTS selfie_url;

-- If you want to keep the data, consider renaming the column instead:
-- ALTER TABLE verification_logs RENAME COLUMN selfie_url TO upload_url;
