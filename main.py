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
from routers import auth, members, teams, positions, candidates, votes, results, election, admin, uploads, support, access_requests, settings, voter, verification_logs
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
# CRITICAL: This must be before all routers are included
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://alm-voting-system.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
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

# 4. AWS Health Check endpoint
@app.get("/api/admin/test-aws")
async def test_aws_connection():
    try:
        import boto3
        import os
        
        key = os.environ.get("AWS_ACCESS_KEY_ID", "")
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        region = os.environ.get("AWS_REGION", "us-east-1")
        
        if not key or not secret:
            return {
                "aws_connected": False,
                "error": "AWS credentials missing",
                "key_present": bool(key),
                "secret_present": bool(secret),
                "region": region
            }
        
        client = boto3.client(
            "rekognition",
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            region_name=region
        )
        
        # Test with a simple list call
        client.list_collections(MaxResults=1)
        
        return {
            "aws_connected": True,
            "region": region,
            "key_prefix": key[:8] + "...",
            "message": "AWS Rekognition is connected"
        }
    except Exception as e:
        return {
            "aws_connected": False,
            "error": str(e),
            "region": os.environ.get("AWS_REGION", "")
        }

# 5. Include all your application router endpoints
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(members.router, prefix="/api/members", tags=["Members"])
app.include_router(teams.router, prefix="/api/teams", tags=["Teams"])
app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["Candidates"])
app.include_router(votes.router, prefix="/api/votes", tags=["Votes"])
app.include_router(verification_logs.router, prefix="/api/verification-logs", tags=["Verification Logs"])
app.include_router(results.router, prefix="/api/results", tags=["Results"])
app.include_router(election.router, prefix="/api/election", tags=["Election"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(support.router, prefix="/api/support", tags=["Support"])
app.include_router(access_requests.router, prefix="/api/access-requests", tags=["Access Requests"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(voter.router, prefix="/api/voter", tags=["Voter"])
