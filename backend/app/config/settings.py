import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "Healthcare Care Gap Automation"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database settings
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:user@localhost:5433/healthcare_care_gap"
    )
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT: str = os.getenv("DATABASE_PORT", "5433")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "healthcare_care_gap")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "postgres")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "user")
    DATABASE_ECHO: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ]
    
    # API settings
    API_HOST: str = os.getenv("API_HOST", "localhost")
    API_PORT: str = os.getenv("API_PORT", "8000")
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # AutoGen settings
    AUTOGEN_CONFIG_PATH: str = os.getenv("AUTOGEN_CONFIG_PATH", "./autogen_config.json")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Email settings
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: str = os.getenv("SMTP_PORT", "587")
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()