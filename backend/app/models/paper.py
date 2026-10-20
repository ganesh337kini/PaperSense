"""
paper.py
Papers table — stores basic metadata for every paper the system has seen,
whether discovered via an academic API (Phase 5) or uploaded by the user
(Phase 7). `source` distinguishes where it came from.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    authors = Column(Text, nullable=True)       # comma-separated for now
    abstract = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    doi = Column(String(255), unique=True, nullable=True, index=True)
    url = Column(String(500), nullable=True)
    source = Column(String(50), nullable=True)  # e.g. "openalex", "arxiv", "upload"
    
    # PDF upload fields
    file_path = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    processing_status = Column(String(50), default="queued")
    processing_error = Column(Text, nullable=True)
    total_pages = Column(Integer, nullable=True)
    
    # Analysis fields
    analysis = Column(Text, nullable=True)  # JSON-structured analysis
    analysis_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One paper has many text chunks (added once we do PDF processing)
    chunks = relationship("PaperChunk", back_populates="paper", cascade="all, delete-orphan")
