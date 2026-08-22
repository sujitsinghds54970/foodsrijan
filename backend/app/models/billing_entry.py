from sqlalchemy import Column, Integer, Float, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class BillingEntry(Base):
    __tablename__ = "billing_entries"

    id = Column(Integer, primary_key=True, index=True)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, nullable=False)
    status = Column(String, default="pending")  # pending, paid, partial, refunded

    patient_id = Column(Integer, ForeignKey("patient_entries.id"))
    patient = relationship("CustomerEntry", backref="billing_entries")