from sqlalchemy import Column, Integer, String, Date, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=False)
    insurance_info = Column(JSON, nullable=True)
    risk_factors = Column(Text, nullable=True)
    preferred_contact_method = Column(String(50), nullable=True, default='email')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    care_gaps = relationship("CareGap", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="patient", cascade="all, delete-orphan")