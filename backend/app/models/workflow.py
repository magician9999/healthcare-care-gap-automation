from sqlalchemy import Column, Integer, String, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .base import Base


class WorkflowStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class Workflow(Base):
    __tablename__ = "workflows"
    
    id = Column(Integer, primary_key=True, index=True)
    campaign_name = Column(String(255), nullable=False, index=True)
    status = Column(Enum(WorkflowStatus), nullable=False, default=WorkflowStatus.PENDING, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_patients = Column(Integer, nullable=False, default=0)
    agents_involved = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaigns = relationship("Campaign", back_populates="workflow", cascade="all, delete-orphan")