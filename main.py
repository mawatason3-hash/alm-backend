from dotenv import load_dotenv
load_dotenv()

import logging
import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from database import connect_db, disconnect_db, create_tables
from routers import auth, members, teams, positions, candidates, votes, results, election, admin, uploads, support, access_requests, settings
import models  # ensure SQLAlchemy Table metadata is registered

logger = logging.getLogger(__name__)
DEBUG = os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    await connect_db()
    yield
    await disconnect_db()

# 1. Initialize the FastAPI app with our lifespan setup
app = FastAPI(title="ALM Voting System Backend", lifespan=lifespan)

# 2. Add CORS Middleware so your Next.js Vercel frontend can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://alm-voting-system.vercel.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Add the Debug Endpoint Route right here
@app.get("/debug/info")
def get_debug_info():
    if os.getenv("DEBUG", "").strip().lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=404, detail="Not Found")
        
    return {
        "status": "healthy",
        "debug_mode": True,
        "database_url_configured": bool(os.getenv("DATABASE_URL")),
        "supabase_url_configured": bool(os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")),
        "python_version": sys.version,
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "production")
    }

# 4. Include all your application router endpoints
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(members.router, prefix="/api/members", tags=["Members"])
app.include_router(teams.router, prefix="/api/teams", tags=["Teams"])
app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["Candidates"])
app.include_router(votes.router, prefix="/api/votes", tags=["Votes"])
app.include_router(results.router, prefix="/api/results", tags=["Results"])
app.include_router(election.router, prefix="/api/election", tags=["Election"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(support.router, prefix="/api/support", tags=["Support"])
app.include_router(access_requests.router, prefix="/api/access-requests", tags=["Access Requests"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
