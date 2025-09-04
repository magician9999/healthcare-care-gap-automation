import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import sys
from pathlib import Path
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_, desc

# Use backend database directly
from ..config.database import SessionLocal
from ..models.patient import Patient
from ..models.care_gap import CareGap, CareGapStatus, PriorityLevel
from ..models.appointment import Appointment, AppointmentStatus
from ..services.llm_service import HealthcareLLMService
from ..services.patient_query_service import PatientQueryService

logger = logging.getLogger(__name__)


class MCPToolsClient:
    """Direct database client for healthcare tools integration"""
    
    def __init__(self):
        self.db_session = None
        
    async def connect(self):
        """Initialize database connection"""
        try:
            self.db_session = SessionLocal()
            logger.info("Connected to healthcare database")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from database"""
        if self.db_session:
            self.db_session.close()
            self.db_session = None
            logger.info("Disconnected from healthcare database")
    
    async def get_overdue_patients(self, **filters) -> Dict[str, Any]:
        """Get overdue patients using direct database queries"""
        if not self.db_session:
            raise RuntimeError("Database session not connected")
            
        try:
            # Get patients with open care gaps
            query = self.db_session.query(Patient).join(CareGap).filter(
                CareGap.status == CareGapStatus.OPEN
            )
            
            # Apply filters
            if filters.get('age_min'):
                query = query.filter(Patient.age >= filters['age_min'])
            if filters.get('age_max'):
                query = query.filter(Patient.age <= filters['age_max'])
            if filters.get('screening_type'):
                query = query.filter(CareGap.screening_type.ilike(f"%{filters['screening_type']}%"))
            if filters.get('priority_level'):
                query = query.filter(CareGap.priority_level == PriorityLevel(filters['priority_level']))
            
            patients = query.limit(filters.get('limit', 20)).all()
            
            patient_list = []
            for patient in patients:
                overdue_gaps = [
                    {
                        "care_gap_id": gap.id,
                        "screening_type": gap.screening_type,
                        "last_screening_date": gap.last_screening_date.isoformat() if gap.last_screening_date else None,
                        "overdue_days": gap.overdue_days,
                        "priority_level": gap.priority_level.value if gap.priority_level else "medium"
                    }
                    for gap in patient.care_gaps if gap.status == CareGapStatus.OPEN
                ]
                
                patient_list.append({
                    "patient_id": patient.id,
                    "name": patient.name,
                    "age": patient.age,
                    "email": patient.email,
                    "overdue_care_gaps": overdue_gaps,
                    "total_care_gaps": len(patient.care_gaps),
                    "open_care_gaps": len(overdue_gaps)
                })
            
            return {
                "status": "success",
                "patients": patient_list,
                "total_count": len(patient_list)
            }
            
        except Exception as e:
            logger.error(f"get_overdue_patients failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_patient_details(self, patient_id: int) -> Dict[str, Any]:
        """Get patient details using direct database queries"""
        if not self.db_session:
            raise RuntimeError("Database session not connected")
            
        try:
            patient = self.db_session.query(Patient).options(
                joinedload(Patient.care_gaps),
                joinedload(Patient.appointments)
            ).filter(Patient.id == patient_id).first()
            
            if not patient:
                return {"status": "error", "message": "Patient not found"}
            
            overdue_gaps = [
                {
                    "care_gap_id": gap.id,
                    "screening_type": gap.screening_type,
                    "last_screening_date": gap.last_screening_date.isoformat() if gap.last_screening_date else None,
                    "overdue_days": gap.overdue_days,
                    "priority_level": gap.priority_level.value if gap.priority_level else "medium"
                }
                for gap in patient.care_gaps if gap.status == CareGapStatus.OPEN
            ]
            
            patient_data = {
                "patient_id": patient.id,
                "name": patient.name,
                "age": patient.age,
                "phone": patient.phone,
                "email": patient.email,
                "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                "risk_factors": patient.risk_factors,
                "preferred_contact_method": patient.preferred_contact_method,
                "overdue_care_gaps": overdue_gaps,
                "total_care_gaps": len(patient.care_gaps),
                "open_care_gaps": len(overdue_gaps),
                "recent_appointments": [
                    {
                        "id": appt.id,
                        "date": appt.appointment_date.isoformat() if appt.appointment_date else None,
                        "doctor_name": appt.doctor_name,
                        "location": appt.location,
                        "status": appt.status.value if appt.status else None
                    }
                    for appt in patient.appointments[-5:] if patient.appointments
                ]
            }
            
            return {
                "status": "success",
                "patient": patient_data
            }
            
        except Exception as e:
            logger.error(f"get_patient_details failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def update_patient_record(self, patient_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update patient record using direct database queries"""
        if not self.db_session:
            raise RuntimeError("Database session not connected")
            
        try:
            patient = self.db_session.query(Patient).filter(Patient.id == patient_id).first()
            
            if not patient:
                return {"status": "error", "message": "Patient not found"}
            
            # Update allowed fields
            allowed_fields = ['phone', 'email', 'risk_factors', 'preferred_contact_method']
            updated_fields = []
            
            for field, value in updates.items():
                if field in allowed_fields and hasattr(patient, field):
                    setattr(patient, field, value)
                    updated_fields.append(field)
            
            if updated_fields:
                patient.updated_at = datetime.utcnow()
                self.db_session.commit()
            
            return {
                "status": "success",
                "message": f"Updated fields: {', '.join(updated_fields)}",
                "patient_id": patient_id,
                "updated_fields": updated_fields
            }
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"update_patient_record failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def close_care_gap(self, care_gap_id: int, completion_date: Optional[str] = None, notes: Optional[str] = None) -> Dict[str, Any]:
        """Close care gap using direct database queries"""
        if not self.db_session:
            raise RuntimeError("Database session not connected")
            
        try:
            care_gap = self.db_session.query(CareGap).filter(CareGap.id == care_gap_id).first()
            
            if not care_gap:
                return {"status": "error", "message": "Care gap not found"}
            
            # Close the care gap
            care_gap.status = CareGapStatus.CLOSED
            care_gap.updated_at = datetime.utcnow()
            self.db_session.commit()
            
            return {
                "status": "success",
                "message": f"Care gap {care_gap_id} closed successfully",
                "care_gap_id": care_gap_id,
                "completion_date": datetime.now().date().isoformat(),
                "screening_type": care_gap.screening_type,
                "notes": notes or "Care gap closed via agent system"
            }
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"close_care_gap failed: {e}")
            return {"status": "error", "message": str(e)}


class BaseHealthcareAgent:
    """Base class for healthcare AutoGen agents"""
    
    def __init__(self, name: str, role: str, system_message: str):
        self.name = name
        self.role = role
        self.system_message = system_message
        self.mcp_client = MCPToolsClient()
        self.llm_service = HealthcareLLMService()
        self.patient_service = PatientQueryService()
        self.conversation_history: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize the agent and MCP connection"""
        success = await self.mcp_client.connect()
        if not success:
            raise RuntimeError(f"Failed to initialize MCP connection for {self.name}")
        
        logger.info(f"Agent {self.name} initialized successfully")
        
    async def cleanup(self):
        """Cleanup agent resources"""
        await self.mcp_client.disconnect()
        logger.info(f"Agent {self.name} cleaned up")
        
    def add_to_conversation(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.name,
            "metadata": metadata or {}
        }
        self.conversation_history.append(message)
        
    async def process_natural_language_query(self, user_prompt: str) -> Dict[str, Any]:
        """Process natural language healthcare queries using LLM services"""
        try:
            # Parse the query using LLM
            query_analysis = await self.llm_service.parse_screening_request(user_prompt)
            
            if not query_analysis.get("screening_tests"):
                return {
                    "status": "error",
                    "message": "Could not understand the requested screening test. Please specify a screening type.",
                    "query_analysis": query_analysis,
                    "agent": self.name
                }
            
            # Query patients based on parsed criteria
            query_results = await self.patient_service.find_patients_by_screening(query_analysis)
            
            if query_results["status"] != "success":
                return {
                    "status": "error",
                    "message": f"Database query failed: {query_results.get('message', 'Unknown error')}",
                    "agent": self.name
                }
            
            # Generate summary using LLM
            patients = query_results["patients"]
            summary = await self.llm_service.generate_patient_summary(patients, query_analysis)
            
            return {
                "status": "success",
                "query_analysis": query_analysis,
                "patients": patients,
                "summary": summary,
                "statistics": query_results.get("statistics"),
                "total_found": len(patients),
                "timestamp": query_results["timestamp"],
                "agent": self.name
            }
            
        except Exception as e:
            logger.error(f"Natural language query processing failed in {self.name}: {e}")
            return {
                "status": "error",
                "message": f"Query processing failed: {str(e)}",
                "agent": self.name
            }

    async def process_message(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process incoming message - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement process_message")
        
    def get_conversation_context(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation context"""
        return self.conversation_history[-limit:] if self.conversation_history else []