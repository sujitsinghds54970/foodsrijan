"""Legacy CustomerEntry model - required for FK compatibility with old models."""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class CustomerEntry(Base):
    __tablename__ = "patient_entries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
