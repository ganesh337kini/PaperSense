"""
config.py
Loads environment variables for the whole backend.
Every other module should import `settings` from here instead of
reading os.environ directly, so we have ONE source of truth.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base backend directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from backend/.env into the process environment
load_dotenv(BASE_DIR / ".env")


class Settings:
    # --- App info ---
    APP_NAME: str = "PaperSense"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"
    BASE_DIR: Path = BASE_DIR

    # --- OpenAI ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'papersense.db'}",
    )

    # --- Embeddings ---
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = 384  # Dimension for all-MiniLM-L6-v2
    FAISS_INDEX_PATH: Path = Path(os.getenv("FAISS_INDEX_PATH", str(BASE_DIR / "faiss_index.bin")))
    FAISS_METADATA_PATH: Path = Path(os.getenv("FAISS_METADATA_PATH", str(BASE_DIR / "faiss_metadata.pkl")))

    # --- File upload ---
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))

    # --- Semantic Scholar / External APIs ---
    SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

    # --- CORS: which frontend origins may call this API ---
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000"]


settings = Settings()
