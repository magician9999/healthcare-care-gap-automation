import os
import logging
from typing import Optional
from pydantic_settings import BaseSettings


class EHRServerSettings(BaseSettings):
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:user@localhost:5433/healthcare_care_gap"
    )
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Security settings
    ENCRYPTION_KEY: Optional[str] = os.getenv("ENCRYPTION_KEY")
    AUDIT_LOG_ENABLED: bool = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"
    
    # MCP Server settings
    MCP_SERVER_NAME: str = "healthcare-ehr-server"
    MCP_SERVER_VERSION: str = "1.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = EHRServerSettings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)