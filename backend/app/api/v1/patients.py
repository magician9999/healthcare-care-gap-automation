from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, and_
import logging

from ...config.database import get_db
from ...models.patient import Patient
from ...models.care_gap import CareGap, PriorityLevel, CareGapStatus
from ...models.appointment import Appointment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patients", tags=["Patients"])


# Pydantic models for API
class PatientResponse(BaseModel):
    id: int
    name: str
    age: int
    email: str
    phone: Optional[str] = None
    date_of_birth: str
    insurance_info: Optional[Dict[str, Any]] = None
    risk_factors: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    total_care_gaps: int = 0
    open_care_gaps: int = 0
    priority_score: Optional[float] = None
    priority_level: Optional[str] = None
    overdue_care_gaps: List[Dict[str, Any]] = []
    recent_appointments: List[Dict[str, Any]] = []
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CareGapResponse(BaseModel):
    id: int
    care_gap_id: int
    screening_type: str
    last_screening_date: Optional[str] = None
    overdue_days: int
    priority_level: str
    status: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    patients: List[PatientResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class PatientFilters(BaseModel):
    search: Optional[str] = None
    min_age: Optional[int] = Field(None, ge=0, le=150)
    max_age: Optional[int] = Field(None, ge=0, le=150)
    screening_type: Optional[str] = None
    min_overdue_days: Optional[int] = Field(None, ge=0)
    max_overdue_days: Optional[int] = Field(None, ge=0)
    priority_level: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    has_open_care_gaps: Optional[bool] = None
    preferred_contact_method: Optional[str] = None


@router.get("/", response_model=PatientListResponse)
async def get_patients(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    sort_by: str = Query("name", pattern="^(name|age|created_at|priority_score)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None, ge=0, le=150),
    max_age: Optional[int] = Query(None, ge=0, le=150),
    screening_type: Optional[str] = Query(None),
    min_overdue_days: Optional[int] = Query(None, ge=0),
    max_overdue_days: Optional[int] = Query(None, ge=0),
    priority_level: Optional[str] = Query(None, pattern="^(low|medium|high|urgent)$"),
    has_open_care_gaps: Optional[bool] = Query(None),
    preferred_contact_method: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of patients with optional filters
    """
    try:
        # Build base query
        query = db.query(Patient)
        
        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Patient.name.ilike(search_term),
                    Patient.email.ilike(search_term)
                )
            )
        
        if min_age is not None:
            query = query.filter(Patient.age >= min_age)
        
        if max_age is not None:
            query = query.filter(Patient.age <= max_age)
        
        if preferred_contact_method:
            query = query.filter(Patient.preferred_contact_method == preferred_contact_method)
        
        # Filter by care gap criteria
        if screening_type or min_overdue_days is not None or max_overdue_days is not None or priority_level or has_open_care_gaps is not None:
            query = query.join(CareGap)
            
            if screening_type:
                query = query.filter(CareGap.screening_type.ilike(f"%{screening_type}%"))
            
            if min_overdue_days is not None:
                query = query.filter(CareGap.overdue_days >= min_overdue_days)
            
            if max_overdue_days is not None:
                query = query.filter(CareGap.overdue_days <= max_overdue_days)
            
            if priority_level:
                query = query.filter(CareGap.priority_level == PriorityLevel(priority_level))
            
            if has_open_care_gaps is not None:
                if has_open_care_gaps:
                    query = query.filter(CareGap.status == CareGapStatus.OPEN)
                else:
                    query = query.filter(CareGap.status != CareGapStatus.OPEN)
        
        # Get total count before pagination
        total = query.distinct().count()
        
        # Apply sorting
        if sort_order == "desc":
            sort_func = desc
        else:
            sort_func = asc
        
        if sort_by == "name":
            query = query.order_by(sort_func(Patient.name))
        elif sort_by == "age":
            query = query.order_by(sort_func(Patient.age))
        elif sort_by == "created_at":
            query = query.order_by(sort_func(Patient.created_at))
        # Note: priority_score would need to be calculated
        
        # Apply pagination
        offset = (page - 1) * per_page
        patients = query.distinct().offset(offset).limit(per_page).all()
        
        # Process patients and add calculated fields
        patient_responses = []
        for patient in patients:
            # Calculate care gap statistics
            total_care_gaps = len(patient.care_gaps)
            open_care_gaps = len([cg for cg in patient.care_gaps if cg.status == CareGapStatus.OPEN])
            
            # Calculate priority score (simplified calculation)
            priority_score = _calculate_priority_score(patient)
            priority_level = _get_priority_level(priority_score)
            
            # Get overdue care gaps
            overdue_care_gaps = [
                {
                    "care_gap_id": cg.id,
                    "screening_type": cg.screening_type,
                    "overdue_days": cg.overdue_days,
                    "priority_level": cg.priority_level.value,
                    "last_screening_date": cg.last_screening_date.isoformat() if cg.last_screening_date else None
                }
                for cg in patient.care_gaps if cg.status == CareGapStatus.OPEN
            ]
            
            # Get recent appointments
            recent_appointments = [
                {
                    "id": apt.id,
                    "date": apt.appointment_date.isoformat() if apt.appointment_date else None,
                    "doctor_name": apt.doctor_name,
                    "location": apt.location,
                    "status": apt.status.value if hasattr(apt.status, 'value') else str(apt.status)
                }
                for apt in sorted(patient.appointments, key=lambda x: x.created_at, reverse=True)[:3]
            ]
            
            patient_response = PatientResponse(
                id=patient.id,
                name=patient.name,
                age=patient.age,
                email=patient.email,
                phone=patient.phone,
                date_of_birth=patient.date_of_birth.isoformat(),
                insurance_info=patient.insurance_info,
                risk_factors=patient.risk_factors,
                preferred_contact_method=patient.preferred_contact_method,
                total_care_gaps=total_care_gaps,
                open_care_gaps=open_care_gaps,
                priority_score=priority_score,
                priority_level=priority_level,
                overdue_care_gaps=overdue_care_gaps,
                recent_appointments=recent_appointments,
                created_at=patient.created_at.isoformat(),
                updated_at=patient.updated_at.isoformat()
            )
            patient_responses.append(patient_response)
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page
        
        return PatientListResponse(
            patients=patient_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
    
    except Exception as e:
        logger.error(f"Failed to get patients: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get patients: {str(e)}")


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(patient_id: int, db: Session = Depends(get_db)):
    """
    Get a specific patient by ID
    """
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Calculate care gap statistics
        total_care_gaps = len(patient.care_gaps)
        open_care_gaps = len([cg for cg in patient.care_gaps if cg.status == CareGapStatus.OPEN])
        
        # Calculate priority score
        priority_score = _calculate_priority_score(patient)
        priority_level = _get_priority_level(priority_score)
        
        # Get overdue care gaps
        overdue_care_gaps = [
            {
                "care_gap_id": cg.id,
                "screening_type": cg.screening_type,
                "overdue_days": cg.overdue_days,
                "priority_level": cg.priority_level.value,
                "last_screening_date": cg.last_screening_date.isoformat() if cg.last_screening_date else None
            }
            for cg in patient.care_gaps if cg.status == CareGapStatus.OPEN
        ]
        
        # Get recent appointments
        recent_appointments = [
            {
                "id": apt.id,
                "date": apt.appointment_date.isoformat() if apt.appointment_date else None,
                "doctor_name": apt.doctor_name,
                "location": apt.location,
                "status": apt.status.value if hasattr(apt.status, 'value') else str(apt.status)
            }
            for apt in sorted(patient.appointments, key=lambda x: x.created_at, reverse=True)[:5]
        ]
        
        return PatientResponse(
            id=patient.id,
            name=patient.name,
            age=patient.age,
            email=patient.email,
            phone=patient.phone,
            date_of_birth=patient.date_of_birth.isoformat(),
            insurance_info=patient.insurance_info,
            risk_factors=patient.risk_factors,
            preferred_contact_method=patient.preferred_contact_method,
            total_care_gaps=total_care_gaps,
            open_care_gaps=open_care_gaps,
            priority_score=priority_score,
            priority_level=priority_level,
            overdue_care_gaps=overdue_care_gaps,
            recent_appointments=recent_appointments,
            created_at=patient.created_at.isoformat(),
            updated_at=patient.updated_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get patient: {str(e)}")


@router.get("/{patient_id}/care-gaps")
async def get_patient_care_gaps(
    patient_id: int,
    status: Optional[str] = Query(None, pattern="^(open|in_progress|closed|cancelled)$"),
    db: Session = Depends(get_db)
):
    """
    Get care gaps for a specific patient
    """
    try:
        # Verify patient exists
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Build query
        query = db.query(CareGap).filter(CareGap.patient_id == patient_id)
        
        if status:
            query = query.filter(CareGap.status == CareGapStatus(status))
        
        care_gaps = query.all()
        
        return [
            {
                "id": cg.id,
                "care_gap_id": cg.id,
                "screening_type": cg.screening_type,
                "last_screening_date": cg.last_screening_date.isoformat() if cg.last_screening_date else None,
                "overdue_days": cg.overdue_days,
                "priority_level": cg.priority_level.value,
                "status": cg.status.value,
                "created_at": cg.created_at.isoformat(),
                "updated_at": cg.updated_at.isoformat()
            }
            for cg in care_gaps
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get care gaps for patient {patient_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get care gaps: {str(e)}")


@router.get("/statistics/overview")
async def get_patient_statistics(db: Session = Depends(get_db)):
    """
    Get overall patient statistics for dashboard
    """
    try:
        total_patients = db.query(Patient).count()
        
        # Patients with open care gaps
        patients_with_open_gaps = db.query(Patient.id).join(CareGap).filter(
            CareGap.status == CareGapStatus.OPEN
        ).distinct().count()
        
        # Total open care gaps
        total_open_care_gaps = db.query(CareGap).filter(
            CareGap.status == CareGapStatus.OPEN
        ).count()
        
        # Urgent care gaps
        urgent_care_gaps = db.query(CareGap).filter(
            and_(
                CareGap.status == CareGapStatus.OPEN,
                CareGap.priority_level == PriorityLevel.URGENT
            )
        ).count()
        
        # High priority care gaps  
        high_priority_care_gaps = db.query(CareGap).filter(
            and_(
                CareGap.status == CareGapStatus.OPEN,
                CareGap.priority_level == PriorityLevel.HIGH
            )
        ).count()
        
        return {
            "total_patients": total_patients,
            "patients_with_open_gaps": patients_with_open_gaps,
            "total_open_care_gaps": total_open_care_gaps,
            "urgent_care_gaps": urgent_care_gaps,
            "high_priority_care_gaps": high_priority_care_gaps,
            "system_health_percentage": 98.5,  # This would be calculated based on system metrics
        }
    
    except Exception as e:
        logger.error(f"Failed to get patient statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


# Helper functions
def _calculate_priority_score(patient: Patient) -> float:
    """
    Calculate priority score for a patient based on age, care gaps, and risk factors
    """
    score = 0.0
    
    # Age factor (higher age = higher priority)
    if patient.age >= 65:
        score += 30
    elif patient.age >= 50:
        score += 20
    elif patient.age >= 40:
        score += 10
    
    # Care gaps factor
    open_care_gaps = [cg for cg in patient.care_gaps if cg.status == CareGapStatus.OPEN]
    
    for gap in open_care_gaps:
        if gap.priority_level == PriorityLevel.URGENT:
            score += 25
        elif gap.priority_level == PriorityLevel.HIGH:
            score += 15
        elif gap.priority_level == PriorityLevel.MEDIUM:
            score += 8
        else:
            score += 3
        
        # Overdue days factor
        if gap.overdue_days > 90:
            score += 15
        elif gap.overdue_days > 30:
            score += 8
        elif gap.overdue_days > 0:
            score += 3
    
    # Risk factors
    if patient.risk_factors:
        score += 10
    
    return round(min(score, 100), 1)  # Cap at 100


def _get_priority_level(score: float) -> str:
    """
    Convert priority score to priority level
    """
    if score >= 70:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 25:
        return "MEDIUM"
    else:
        return "LOW"