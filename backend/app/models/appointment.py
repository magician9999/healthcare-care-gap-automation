from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .base import Base


class AppointmentStatus(enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    care_gap_id = Column(Integer, ForeignKey("care_gaps.id"), nullable=False, index=True)
    appointment_date = Column(DateTime, nullable=False, index=True)
    doctor_name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    status = Column(Enum(AppointmentStatus), nullable=False, default=AppointmentStatus.SCHEDULED, index=True)
    confirmation_code = Column(String(50), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    care_gap = relationship("CareGap", back_populates="appointments")