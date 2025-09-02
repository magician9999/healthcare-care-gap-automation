import sys
import os
from pathlib import Path

# Add the backend app directory to the Python path for model imports
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import logging
from contextlib import contextmanager
from typing import Generator

from app.models.base import Base
from app.models.patient import Patient
from app.models.care_gap import CareGap, CareGapStatus, PriorityLevel
from app.models.appointment import Appointment, AppointmentStatus
from config import settings

logger = logging.getLogger(__name__)

# Database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_database_session() -> Session:
    """Get database session"""
    return SessionLocal()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions with automatic cleanup"""
    session = SessionLocal()
    try:
        yield session
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def test_database_connection() -> bool:
    """Test database connectivity"""
    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


# Export models for easy access
__all__ = [
    "get_database_session",
    "get_db_session", 
    "test_database_connection",
    "create_tables",
    "Patient",
    "CareGap",
    "CareGapStatus",
    "PriorityLevel",
    "Appointment",
    "AppointmentStatus", 
    "Session",
    "SessionLocal"
]