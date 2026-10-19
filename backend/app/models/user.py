"""
user.py
Users table. Authentication (password hashing/login) is added in Phase 22 —
for now this just defines the table shape so relationships (e.g. ResearchQueries
belonging to a user) can be wired up early.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # One user can have many research queries
    queries = relationship("ResearchQuery", back_populates="user")
