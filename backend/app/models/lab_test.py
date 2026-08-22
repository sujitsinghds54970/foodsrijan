from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class LabMenuItem(Base):
    __tablename__ = "lab_menu_items"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patient_entries.id"))
    technician_id = Column(Integer, ForeignKey("users.id"))
    test_type = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, completed
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("CustomerEntry", backref="lab_menu_items")
    technician = relationship("User", backref="lab_menu_items")
    result = Column(Text, nullable=True)