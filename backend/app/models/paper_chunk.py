"""
paper_chunk.py
PaperChunks table — each row is one chunk of text from a paper.
Includes layout-aware bounding box coordinates extracted via PyMuPDF.
"""

from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class PaperChunk(Base):
    __tablename__ = "paper_chunks"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    section = Column(String(100), nullable=True)   # e.g. "Abstract", "Methodology"
    text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=True)    # order within the paper
    page_number = Column(Integer, nullable=True)   # page number in PDF
    embedding_reference = Column(String(100), nullable=True)  # FAISS vector id

    # Layout-aware bounding box coordinates (PDF points, origin top-left)
    bbox_x0 = Column(Float, nullable=True)
    bbox_y0 = Column(Float, nullable=True)
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)

    # Block type: text | equation | table | figure
    block_type = Column(String(50), nullable=True, default="text")

    # Vision-LLM generated description for figure blocks
    figure_description = Column(Text, nullable=True)

    paper = relationship("Paper", back_populates="chunks")
