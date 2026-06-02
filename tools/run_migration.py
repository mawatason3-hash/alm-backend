"""Run a SQL migration file against the configured PostgreSQL database.

Usage:
  python tools/run_migration.py migrations/001_drop_selfie_url.sql

Environment:
  DATABASE_URL: database connection URL
  DB_SSL: optional, set to 1/true/yes to enable ssl=true in the URL
"""
import os
import sys
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import psycopg2
from psycopg2.extras import RealDictCursor


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def add_ssl_if_requested(url: str) -> str:
    db_ssl = os.getenv("DB_SSL", "").strip().lower()
    if db_ssl in {"1", "true", "yes"}:
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["sslmode"] = query.get("sslmode", "require")
        url = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
    return url


def load_sql(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def execute_migration(sql: str, database_url: str) -> None:
    conn = psycopg2.connect(database_url)
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql)
    finally:
        conn.close()


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python tools/run_migration.py <migration-sql-file>")
        return 1

    migration_path = sys.argv[1]
    if not os.path.isfile(migration_path):
        print(f"Migration file not found: {migration_path}")
        return 1

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL environment variable must be set.")
        return 1

    database_url = normalize_database_url(database_url)
    database_url = add_ssl_if_requested(database_url)

    sql = load_sql(migration_path)
    print(f"Running migration: {migration_path}")
    execute_migration(sql, database_url)
    print("Migration completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
