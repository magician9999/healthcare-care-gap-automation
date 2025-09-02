from fastapi import APIRouter
from .agents import router as agents_router
from .patients import router as patients_router

router = APIRouter()

# Include routers
router.include_router(agents_router)
router.include_router(patients_router)

# API status endpoint
@router.get("/status")
async def api_status():
    """API status endpoint"""
    return {"status": "API v1 is running", "version": "1.0.0"}