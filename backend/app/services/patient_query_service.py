"""
Patient Query Service for healthcare care gap database queries
Handles complex database queries based on LLM-parsed criteria
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import and_, or_, desc, func

from ..config.database import engine
from ..models.patient import Patient
from ..models.care_gap import CareGap, PriorityLevel, CareGapStatus
from ..models.appointment import Appointment, AppointmentStatus

logger = logging.getLogger(__name__)


class PatientQueryService:
    """Service for querying patient care gap data based on LLM-parsed criteria"""
    
    def __init__(self):
        SessionLocal = sessionmaker(bind=engine)
        self.db_session = SessionLocal
    
    async def find_patients_by_screening(self, query_criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Find patients based on screening test criteria from LLM parsing"""
        
        db = self.db_session()
        try:
            # Extract criteria
            screening_tests = query_criteria.get("screening_tests", [])
            patient_criteria = query_criteria.get("patient_criteria", {})
            time_criteria = query_criteria.get("time_criteria", {})
            
            # Build base query
            query = db.query(Patient, CareGap).join(CareGap, Patient.id == CareGap.patient_id)
            
            # Filter by screening tests
            if screening_tests and "all" not in screening_tests:
                query = query.filter(CareGap.screening_type.in_(screening_tests))
            
            # Filter by overdue status
            if time_criteria.get("overdue_only", True):
                query = query.filter(CareGap.status == CareGapStatus.OPEN)
                query = query.filter(CareGap.overdue_days > 0)
            
            # Filter by time period
            time_period = time_criteria.get("time_period")
            if time_period:
                cutoff_date = self._calculate_cutoff_date(time_period)
                query = query.filter(CareGap.last_screening_date >= cutoff_date)
            
            # Filter by patient criteria
            age_range = patient_criteria.get("age_range")
            if age_range:
                if age_range[0] is not None:
                    query = query.filter(Patient.age >= age_range[0])
                if age_range[1] is not None:
                    query = query.filter(Patient.age <= age_range[1])
            
            gender = patient_criteria.get("gender")
            if gender:
                # Simple gender inference based on name patterns (for demo purposes)
                if gender.lower() == "female":
                    query = query.filter(~Patient.name.ilike('%john%'))
                elif gender.lower() == "male":
                    query = query.filter(~Patient.name.ilike('%sarah%'))
            
            # Filter by priority level
            priority_level = patient_criteria.get("priority_level")
            if priority_level:
                priority_enum = getattr(PriorityLevel, priority_level.upper(), None)
                if priority_enum:
                    query = query.filter(CareGap.priority_level == priority_enum)
            
            # Order by priority and overdue days
            query = query.order_by(
                desc(CareGap.priority_level),
                desc(CareGap.overdue_days),
                Patient.name
            )
            
            # Execute query
            results = query.all()
            
            # Process results
            patients_data = []
            for patient, care_gap in results:
                patient_dict = {
                    "patient_id": patient.id,
                    "care_gap_id": care_gap.id,  # Include care gap ID for booking functionality
                    "name": patient.name,
                    "age": patient.age,
                    "email": patient.email,
                    "phone": patient.phone,
                    "screening_type": care_gap.screening_type,
                    "last_screening_date": care_gap.last_screening_date.isoformat() if care_gap.last_screening_date else None,
                    "overdue_days": care_gap.overdue_days,
                    "priority_level": care_gap.priority_level.value if care_gap.priority_level else "medium",
                    "status": care_gap.status.value,
                    "risk_factors": patient.risk_factors,
                    "preferred_contact_method": patient.preferred_contact_method,
                    "created_at": care_gap.created_at.isoformat()
                }
                patients_data.append(patient_dict)
            
            # Generate statistics
            stats = self._generate_query_statistics(patients_data, query_criteria)
            
            return {
                "status": "success",
                "patients": patients_data,
                "statistics": stats,
                "query_criteria": query_criteria,
                "total_found": len(patients_data),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Patient query failed: {e}")
            return {
                "status": "error",
                "message": f"Database query failed: {str(e)}",
                "patients": [],
                "total_found": 0
            }
        finally:
            db.close()
    
    def _calculate_cutoff_date(self, time_period: str) -> date:
        """Calculate cutoff date based on time period"""
        today = date.today()
        
        if time_period == "3_months":
            return today - timedelta(days=90)
        elif time_period == "6_months":
            return today - timedelta(days=180)
        elif time_period == "1_year":
            return today - timedelta(days=365)
        else:
            return today - timedelta(days=90)  # Default to 3 months
    
    def _generate_query_statistics(self, patients_data: List[Dict], query_criteria: Dict) -> Dict[str, Any]:
        """Generate statistics for the query results"""
        
        if not patients_data:
            return {
                "total_patients": 0,
                "priority_distribution": {},
                "screening_distribution": {},
                "average_overdue_days": 0
            }
        
        # Priority distribution
        priority_counts = {}
        for patient in patients_data:
            priority = patient.get("priority_level", "medium")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Screening type distribution
        screening_counts = {}
        for patient in patients_data:
            screening = patient.get("screening_type", "unknown")
            screening_counts[screening] = screening_counts.get(screening, 0) + 1
        
        # Average overdue days
        total_overdue_days = sum(patient.get("overdue_days", 0) for patient in patients_data)
        avg_overdue_days = total_overdue_days / len(patients_data) if patients_data else 0
        
        # Age distribution
        age_ranges = {"18-39": 0, "40-64": 0, "65-74": 0, "75+": 0}
        for patient in patients_data:
            age = patient.get("age", 0)
            if age < 40:
                age_ranges["18-39"] += 1
            elif age < 65:
                age_ranges["40-64"] += 1
            elif age < 75:
                age_ranges["65-74"] += 1
            else:
                age_ranges["75+"] += 1
        
        return {
            "total_patients": len(patients_data),
            "priority_distribution": priority_counts,
            "screening_distribution": dict(sorted(screening_counts.items(), key=lambda x: x[1], reverse=True)),
            "age_distribution": age_ranges,
            "average_overdue_days": round(avg_overdue_days, 1),
            "most_overdue_patient": max(patients_data, key=lambda x: x.get("overdue_days", 0)) if patients_data else None,
            "query_summary": {
                "screening_tests": query_criteria.get("screening_tests", []),
                "overdue_only": query_criteria.get("time_criteria", {}).get("overdue_only", True),
                "time_period": query_criteria.get("time_criteria", {}).get("time_period")
            }
        }
    
    async def get_patient_details_with_care_gaps(self, patient_id: int) -> Dict[str, Any]:
        """Get detailed patient information including all care gaps"""
        
        db = self.db_session()
        try:
            # Get patient
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                return {
                    "status": "error",
                    "message": f"Patient with ID {patient_id} not found"
                }
            
            # Get all care gaps for this patient
            care_gaps = db.query(CareGap).filter(CareGap.patient_id == patient_id).all()
            
            # Get appointments
            appointments = db.query(Appointment).filter(Appointment.patient_id == patient_id).all()
            
            # Format care gaps
            care_gaps_data = []
            for gap in care_gaps:
                gap_dict = {
                    "id": gap.id,
                    "screening_type": gap.screening_type,
                    "last_screening_date": gap.last_screening_date.isoformat() if gap.last_screening_date else None,
                    "overdue_days": gap.overdue_days,
                    "priority_level": gap.priority_level.value if gap.priority_level else "medium",
                    "status": gap.status.value,
                    "created_at": gap.created_at.isoformat(),
                    "updated_at": gap.updated_at.isoformat()
                }
                care_gaps_data.append(gap_dict)
            
            # Format appointments
            appointments_data = []
            for appt in appointments:
                appt_dict = {
                    "id": appt.id,
                    "appointment_date": appt.appointment_date.isoformat(),
                    "doctor_name": appt.doctor_name,
                    "location": appt.location,
                    "status": appt.status.value,
                    "confirmation_code": appt.confirmation_code
                }
                appointments_data.append(appt_dict)
            
            return {
                "status": "success",
                "patient": {
                    "id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "email": patient.email,
                    "phone": patient.phone,
                    "date_of_birth": patient.date_of_birth.isoformat(),
                    "insurance_info": patient.insurance_info,
                    "risk_factors": patient.risk_factors,
                    "preferred_contact_method": patient.preferred_contact_method,
                    "care_gaps": care_gaps_data,
                    "appointments": appointments_data,
                    "total_care_gaps": len(care_gaps_data),
                    "open_care_gaps": len([g for g in care_gaps_data if g["status"] == "open"]),
                    "urgent_care_gaps": len([g for g in care_gaps_data if g["priority_level"] == "urgent"])
                }
            }
            
        except Exception as e:
            logger.error(f"Patient details query failed: {e}")
            return {
                "status": "error",
                "message": f"Failed to retrieve patient details: {str(e)}"
            }
        finally:
            db.close()
    
    async def search_patients_by_name_or_email(self, search_term: str) -> Dict[str, Any]:
        """Search patients by name or email"""
        
        db = self.db_session()
        try:
            # Search by name or email (case insensitive)
            query = db.query(Patient).filter(
                or_(
                    Patient.name.ilike(f"%{search_term}%"),
                    Patient.email.ilike(f"%{search_term}%")
                )
            ).limit(20)  # Limit results
            
            patients = query.all()
            
            patients_data = []
            for patient in patients:
                # Get care gap summary
                care_gaps = db.query(CareGap).filter(CareGap.patient_id == patient.id).all()
                open_gaps = [g for g in care_gaps if g.status == CareGapStatus.OPEN]
                
                patient_dict = {
                    "id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "email": patient.email,
                    "phone": patient.phone,
                    "total_care_gaps": len(care_gaps),
                    "open_care_gaps": len(open_gaps),
                    "urgent_gaps": len([g for g in care_gaps if g.priority_level == PriorityLevel.URGENT])
                }
                patients_data.append(patient_dict)
            
            return {
                "status": "success",
                "patients": patients_data,
                "total_found": len(patients_data),
                "search_term": search_term
            }
            
        except Exception as e:
            logger.error(f"Patient search failed: {e}")
            return {
                "status": "error",
                "message": f"Search failed: {str(e)}",
                "patients": []
            }
        finally:
            db.close()