"""
database.py
Sets up the SQLAlchemy engine + session for PostgreSQL, and exposes:
  - Base:    the declarative base every model class inherits from
  - engine:  the actual DB connection pool
  - get_db:  a FastAPI dependency that hands routes a DB session
             and always closes it afterward, even on error.

Every model file (app/models/*.py) imports `Base` from here.
Every route that touches the DB will use `Depends(get_db)` (from Phase 3 onward).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# `echo=settings.DEBUG` prints every SQL statement to the terminal while
# DEBUG=True in .env — handy for seeing exactly what's happening, turn off
# in production by setting DEBUG=False.
# SQLite doesn't support multiple threads, so we add check_same_thread=False
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency: yields a DB session for a single request,
    then closes it automatically once the request is done.
    Usage in a route:
        def some_route(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
