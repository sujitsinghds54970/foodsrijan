from sqlalchemy import Column, Integer, String, Time, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.database import Base

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    calendar_day_id = Column(Integer, ForeignKey("calendar_days.id"), nullable=False)
    time_slot = Column(Time, nullable=False)
    status = Column(String, default="scheduled")  # scheduled, completed, cancelled

    patient = relationship("Customer", back_populates="appointments")
    calendar_day = relationship("CalendarDay", back_populates="appointments")