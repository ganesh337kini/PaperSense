"""
paper_chunk.py
PaperChunks table — each row is one chunk of text from a paper (e.g. one
paragraph of the Methodology section). `embedding_reference` will store the
FAISS index ID once embeddings are added (Phase 11-12) — the actual vector
lives in FAISS, not in Postgres; this column just links the two.
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class PaperChunk(Base):
    __tablename__ = "paper_chunks"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    section = Column(String(100), nullable=True)   # e.g. "Abstract", "Methodology"
    text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=True)    # order within the paper
    embedding_reference = Column(String(100), nullable=True)  # FAISS vector id

    paper = relationship("Paper", back_populates="chunks")
