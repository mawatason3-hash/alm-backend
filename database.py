import logging
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from databases import Database
from sqlalchemy import create_engine, MetaData, inspect, text
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable must be set")

# Fix Railway PostgreSQL URL format if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Support optional TLS for managed Postgres providers.
# Set DB_SSL=true in .env or environment variables when the server requires SSL.
DB_SSL = os.getenv("DB_SSL", "").strip().lower()
if DB_SSL in {"1", "true", "yes"}:
    parsed_url = urlparse(DATABASE_URL)
    query = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
    query["ssl"] = "true"
    DATABASE_URL = urlunparse(parsed_url._replace(query=urlencode(query, doseq=True)))
    logger.info("Using database URL with ssl=true")

database = Database(
    DATABASE_URL,
    min_size=int(os.getenv("DB_MIN_SIZE", 1)),
    max_size=int(os.getenv("DB_MAX_SIZE", 10)),
    timeout=30,
)
metadata = MetaData()
engine = create_engine(
    DATABASE_URL.replace("+asyncpg", ""),
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", 5)),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", 10)),
)

async def connect_db():
    try:
        await database.connect()
    except Exception as exc:
        logger.error("Database connection failed: %s", exc, exc_info=True)
        raise

async def disconnect_db():
    try:
        await database.disconnect()
    except Exception as exc:
        logger.warning("Database disconnect failed: %s", exc, exc_info=True)

def create_tables():
    metadata.create_all(engine)
    ensure_users_photo_url()


def ensure_users_photo_url():
    """Ensure the deployed users table has the photo_url column."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("users")}
    if "photo_url" in existing_columns:
        return

    with engine.begin() as connection:
        connection.execute(text('ALTER TABLE "users" ADD COLUMN "photo_url" TEXT'))
