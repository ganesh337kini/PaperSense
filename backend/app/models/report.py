"""
report.py
Reports table — stores the final generated report content (as text/JSON)
tied back to the query that produced it.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("research_queries.id"), nullable=False)
    report_content = Column(Text, nullable=False)  # JSON-serialized report structure
    created_at = Column(DateTime, default=datetime.utcnow)

    query = relationship("ResearchQuery", back_populates="reports")
