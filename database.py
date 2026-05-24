import os
from databases import Database
from sqlalchemy import create_engine, MetaData
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable must be set")

# Fix Railway PostgreSQL URL format if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

database = Database(DATABASE_URL)
metadata = MetaData()
engine = create_engine(DATABASE_URL.replace("+asyncpg", ""))

async def connect_db():
    await database.connect()
    
async def disconnect_db():
    await database.disconnect()

def create_tables():
    metadata.create_all(engine)
