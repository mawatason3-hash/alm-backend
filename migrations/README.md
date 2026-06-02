Migration plan: remove selfie-related DB columns

1) Backup your database (very important).

2) Inspect existing data in the `verification_logs` table:
   - If you want to preserve `selfie_url`, export the column first or rename it to `upload_url`.

3) Apply migration SQL located at `migrations/001_drop_selfie_url.sql`.
   - Example (Postgres):
     psql "postgresql://USER:PASS@HOST:PORT/DBNAME" -f migrations/001_drop_selfie_url.sql

4) Update application code (already done in `models.py`) and restart the backend.

5) Run the app and verify admin pages that previously showed uploads render correctly (they will use `upload_url` alias in API responses).

Notes:
- If you use a managed DB or CI, run migration in a maintenance window.
- If you prefer non-destructive change, rename the column instead of dropping it.
