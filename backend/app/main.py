import logging
import traceback
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings, create_tables
from .api.v1 import router as api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up Healthcare Care Gap Automation API...")
    try:
        create_tables()
        logger.info("Database tables created/verified successfully")
        
        # Initialize AutoGen workflow service
        from .api.v1.agents import initialize_workflow_service
        await initialize_workflow_service()
        logger.info("AutoGen workflow service initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Healthcare Care Gap Automation API...")
    try:
        from .api.v1.agents import cleanup_workflow_service
        await cleanup_workflow_service()
        logger.info("AutoGen workflow service cleaned up")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Healthcare Care Gap Automation System using FastAPI, PostgreSQL, and AutoGen",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Custom exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Exception",
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error: {exc} - {request.url}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "status_code": 422,
            "path": str(request.url)
        }
    )

@app.exception_handler(StarletteHTTPException)
async def starlette_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle Starlette HTTP exceptions"""
    logger.warning(f"Starlette HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Exception", 
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc} - {request.url}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "status_code": 500,
            "path": str(request.url)
        }
    )

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint to verify the API is running
    """
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG
    }

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production"
    }