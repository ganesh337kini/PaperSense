"""
main.py
Entry point for the PaperSense backend.

Run with (from backend/ folder, venv active):
    uvicorn app.main:app --reload

This file, in Phase 1, does three things:
1. Creates the FastAPI app.
2. Enables CORS so the HTML/CSS/JS frontend (served separately) can call the API.
3. Serves the frontend's static files (HTML/CSS/JS) directly, so you can open
   http://127.0.0.1:8000 and see a real page, not just /docs.

Later phases will add routers under app/api/ (search.py, upload.py, etc.)
and include them here with app.include_router(...).
"""

from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.api.search import router as search_router
from app.api.upload import router as upload_router
from app.api.analysis import router as analysis_router

# Importing the models registers them with Base's metadata, so
# Base.metadata.create_all() below knows about every table.
from app.models import user, paper, paper_chunk, research_query, report  # noqa: F401

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
)

# Research-paper search API
app.include_router(search_router, prefix="/api", tags=["search"])

# PDF upload and management API
app.include_router(upload_router, prefix="/api", tags=["upload"])

# Paper analysis, comparison, and report generation API
app.include_router(analysis_router, prefix="/api", tags=["analysis"])

# Create all tables (users, papers, paper_chunks, research_queries, reports)
# if they don't already exist. This is fine for development; a real migration
# tool (Alembic) would replace this in a production setup, but for a
# final-year project this keeps things simple and transparent.
Base.metadata.create_all(bind=engine)

# Allow the frontend to call this API without CORS errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Path to the frontend folder (../../frontend relative to this file) ----
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/api/health")
def health_check():
    """Simple endpoint to confirm the backend is alive and reachable."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/api/db-health")
def db_health_check(db: Session = Depends(get_db)):
    """
    Confirms the backend can actually talk to PostgreSQL, and lists which
    tables exist. If DATABASE_URL in .env is wrong, this endpoint will
    return a 500 error with the underlying connection error message.
    """
    result = db.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
    )
    tables = [row[0] for row in result]
    return {
        "status": "connected",
        "database": settings.DATABASE_URL.split("@")[-1],  # hides credentials
        "tables": tables,
    }


# Serve CSS/JS as static files under /static
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_frontend():
    """Serves the main frontend page at the root URL."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))
