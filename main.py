from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from database import connect_db, disconnect_db, create_tables
from routers import auth, members, teams, positions, candidates, votes, results, election, admin, uploads
import models  # ensure SQLAlchemy Table metadata is registered

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    await connect_db()
    yield
    await disconnect_db()

os.makedirs(os.path.join("static", "uploads"), exist_ok=True)

app = FastAPI(
    title="ALM Voting System API",
    description="Association of Liberians in Musanze - Election Platform",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=True,
)

# Allow all origins by default so the frontend can migrate to Netlify without CORS failures.
# If you want to lock this down later, set ALLOWED_ORIGINS in env as a comma-separated list.
allowed_origins = ["*"]
custom_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
if custom_origins:
    allowed_origins = custom_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"detail": exc.detail or "Not Found"}, status_code=exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": exc.errors()}, status_code=422)

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse({"detail": str(exc)}, status_code=500)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(members.router, prefix="/api/members", tags=["Members"])
app.include_router(teams.router, prefix="/api/teams", tags=["Teams"])
app.include_router(positions.router, prefix="/api/positions", tags=["Positions"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["Candidates"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(votes.router, prefix="/api/votes", tags=["Votes"])
app.include_router(results.router, prefix="/api/results", tags=["Results"])
app.include_router(election.router, prefix="/api/election", tags=["Election"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

@app.get("/")
async def root():
    return {
        "message": "ALM Voting System API",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0"
    print(f"[SERVER STARTUP] Binding to host: {host} on port: {port}")
    # bind to 0.0.0.0 to be reachable externally on hosting platforms
    uvicorn.run("main:app", host=host, port=port)
