from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .base import Base


class PriorityLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class CareGapStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress" 
    CLOSED = "closed"
    CANCELLED = "cancelled"


class CareGap(Base):
    __tablename__ = "care_gaps"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    screening_type = Column(String(100), nullable=False, index=True)
    last_screening_date = Column(Date, nullable=True)
    overdue_days = Column(Integer, nullable=False, default=0)
    priority_level = Column(Enum(PriorityLevel), nullable=False, default=PriorityLevel.MEDIUM)
    status = Column(Enum(CareGapStatus), nullable=False, default=CareGapStatus.OPEN, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="care_gaps")
    appointments = relationship("Appointment", back_populates="care_gap", cascade="all, delete-orphan")