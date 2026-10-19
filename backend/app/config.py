"""
config.py
Loads environment variables for the whole backend.
Every other module should import `settings` from here instead of
reading os.environ directly, so we have ONE source of truth.
"""

import os
from dotenv import load_dotenv

# Load variables from backend/.env into the process environment
load_dotenv()


class Settings:
    # --- App info ---
    APP_NAME: str = "PaperSense"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"

    # --- OpenAI ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/papersense",
    )

    # --- Embeddings ---
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = 384  # Dimension for all-MiniLM-L6-v2

    # --- File upload ---
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")

    # --- CORS: which frontend origins may call this API ---
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]


settings = Settings()
