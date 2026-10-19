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
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"

    # --- OpenAI ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # --- Database (added in Phase 2, defined now so config is stable) ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/papersense",
    )

    # --- CORS: which frontend origins may call this API ---
    ALLOWED_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]


settings = Settings()
