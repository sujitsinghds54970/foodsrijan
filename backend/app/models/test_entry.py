from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class MenuItemEntry(Base):
    __tablename__ = "test_entries"

    id = Column(Integer, primary_key=True, index=True)
    test_name = Column(String, nullable=False)
    result = Column(String, nullable=True)
    price = Column(Float, nullable=False)

    patient_id = Column(Integer, ForeignKey("patient_entries.id"))
    patient = relationship("CustomerEntry", backref="test_entries")