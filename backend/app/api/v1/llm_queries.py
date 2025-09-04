"""
LLM-powered healthcare query endpoints
Handles natural language queries for patient care gap analysis
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ...services.llm_service import HealthcareLLMService
from ...services.patient_query_service import PatientQueryService
from ...config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Healthcare Queries"])

# Initialize services
llm_service = HealthcareLLMService()
patient_service = PatientQueryService()


class HealthcareQueryRequest(BaseModel):
    """Request model for healthcare queries"""
    prompt: str
    include_summary: bool = True
    max_results: Optional[int] = 100


class HealthcareQueryResponse(BaseModel):
    """Response model for healthcare queries"""
    status: str
    patients: list
    summary: Optional[str] = None
    query_analysis: Dict[str, Any]
    statistics: Optional[Dict[str, Any]] = None
    total_found: int
    timestamp: str


@router.post("/query", response_model=HealthcareQueryResponse)
async def process_healthcare_query(request: HealthcareQueryRequest):
    """
    Process natural language healthcare queries to find patients with care gaps
    
    Examples:
    - "Show me patients who need mammograms"
    - "Find urgent colonoscopy patients from last 3 months"
    - "List overdue diabetes screenings for seniors"
    - "Patients needing blood pressure checks"
    """
    try:
        # Check if OpenAI API key is available
        if not settings.OPENAI_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured. Please add OPENAI_API_KEY to environment variables."
            )
        
        logger.info(f"Processing healthcare query: {request.prompt}")
        
        # Step 1: Parse the natural language query using LLM
        query_analysis = await llm_service.parse_screening_request(request.prompt)
        
        if not query_analysis.get("screening_tests"):
            return HealthcareQueryResponse(
                status="error",
                patients=[],
                query_analysis=query_analysis,
                total_found=0,
                timestamp="",
                summary="Could not understand the requested screening test. Please specify a screening type like 'mammogram', 'colonoscopy', 'blood pressure', etc."
            )
        
        # Step 2: Query the database based on parsed criteria
        query_results = await patient_service.find_patients_by_screening(query_analysis)
        
        if query_results["status"] != "success":
            raise HTTPException(
                status_code=500,
                detail=f"Database query failed: {query_results.get('message', 'Unknown error')}"
            )
        
        patients = query_results["patients"]
        
        # Limit results if specified
        if request.max_results and len(patients) > request.max_results:
            patients = patients[:request.max_results]
        
        # Step 3: Generate natural language summary if requested
        summary = None
        if request.include_summary:
            try:
                summary = await llm_service.generate_patient_summary(patients, query_analysis)
            except Exception as e:
                logger.warning(f"Summary generation failed: {e}")
                summary = f"Found {len(patients)} patients matching your criteria."
        
        return HealthcareQueryResponse(
            status="success",
            patients=patients,
            summary=summary,
            query_analysis=query_analysis,
            statistics=query_results.get("statistics"),
            total_found=len(query_results["patients"]),  # Total before limiting
            timestamp=query_results["timestamp"]
        )
        
    except Exception as e:
        logger.error(f"Healthcare query processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


@router.get("/patient/{patient_id}")
async def get_patient_details(patient_id: int):
    """
    Get detailed information for a specific patient including all care gaps
    """
    try:
        patient_details = await patient_service.get_patient_details_with_care_gaps(patient_id)
        
        if patient_details["status"] != "success":
            raise HTTPException(
                status_code=404,
                detail=patient_details["message"]
            )
        
        return patient_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Patient details retrieval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve patient details: {str(e)}"
        )


@router.get("/search")
async def search_patients(query: str):
    """
    Search patients by name or email
    """
    try:
        if len(query.strip()) < 2:
            raise HTTPException(
                status_code=400,
                detail="Search query must be at least 2 characters long"
            )
        
        search_results = await patient_service.search_patients_by_name_or_email(query)
        
        return search_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Patient search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/analyze")
async def analyze_query_intent(request: HealthcareQueryRequest):
    """
    Analyze query intent without executing database search
    Useful for understanding what the LLM extracted from the query
    """
    try:
        if not settings.OPENAI_API_KEY:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured"
            )
        
        query_analysis = await llm_service.parse_screening_request(request.prompt)
        
        return {
            "status": "success",
            "query_analysis": query_analysis,
            "timestamp": query_analysis.get("parsed_at")
        }
        
    except Exception as e:
        logger.error(f"Query analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/screening-tests")
async def get_available_screening_tests():
    """
    Get list of available screening tests that can be queried
    """
    return {
        "status": "success",
        "screening_tests": {
            "mammography": {
                "name": "Mammography",
                "description": "Breast cancer screening",
                "keywords": ["mammogram", "mammography", "breast cancer screening", "breast scan"]
            },
            "colonoscopy": {
                "name": "Colonoscopy", 
                "description": "Colorectal cancer screening",
                "keywords": ["colonoscopy", "colon cancer screening", "colorectal screening"]
            },
            "pap_smear": {
                "name": "Pap Smear",
                "description": "Cervical cancer screening",
                "keywords": ["pap smear", "pap test", "cervical cancer screening"]
            },
            "blood_pressure_check": {
                "name": "Blood Pressure Check",
                "description": "Hypertension screening",
                "keywords": ["blood pressure", "bp check", "hypertension screening"]
            },
            "cholesterol_screening": {
                "name": "Cholesterol Screening",
                "description": "Lipid panel testing",
                "keywords": ["cholesterol", "lipid panel", "cholesterol test"]
            },
            "diabetes_screening": {
                "name": "Diabetes Screening",
                "description": "Blood sugar and A1C testing",
                "keywords": ["diabetes", "blood sugar", "glucose test", "a1c"]
            },
            "bone_density_scan": {
                "name": "Bone Density Scan",
                "description": "Osteoporosis screening",
                "keywords": ["bone density", "dexa scan", "osteoporosis screening"]
            },
            "eye_exam": {
                "name": "Eye Exam",
                "description": "Vision and eye health screening",
                "keywords": ["eye exam", "vision test", "ophthalmology"]
            },
            "skin_cancer_screening": {
                "name": "Skin Cancer Screening",
                "description": "Dermatological examination",
                "keywords": ["skin cancer", "dermatology", "mole check"]
            },
            "prostate_screening": {
                "name": "Prostate Screening",
                "description": "PSA test and prostate examination",
                "keywords": ["prostate", "psa test", "prostate cancer screening"]
            }
        },
        "example_queries": [
            "Show me patients who need mammograms",
            "Find urgent colonoscopy patients from last 3 months",
            "List overdue diabetes screenings for seniors",
            "Patients needing blood pressure checks",
            "Show me all screening gaps for Shivanshu Saxena"
        ]
    }