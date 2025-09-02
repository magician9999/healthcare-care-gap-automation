from fastapi import APIRouter
from .agents import router as agents_router

router = APIRouter()

# Include agents router
router.include_router(agents_router)

# API status endpoint
@router.get("/status")
async def api_status():
    """API status endpoint"""
    return {"status": "API v1 is running", "version": "1.0.0"}