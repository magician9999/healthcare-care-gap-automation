from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .base import Base


class CampaignStatus(enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    filters = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(Enum(CampaignStatus), nullable=False, default=CampaignStatus.DRAFT, index=True)
    results_summary = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships  
    workflow = relationship("Workflow", back_populates="campaigns")