#!/usr/bin/env python3

import asyncio
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Sequence
from sqlalchemy.orm import joinedload
from sqlalchemy import and_, or_

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializeResult
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import mcp.types as types

from database import (
    get_db_session,
    test_database_connection,
    Patient,
    CareGap,
    CareGapStatus,
    PriorityLevel,
    Appointment
)
from security import security_manager, data_validator
from config import settings, logger

# MCP Server instance
server = Server(settings.MCP_SERVER_NAME)


@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available EHR resources"""
    return [
        Resource(
            uri="ehr://patients/overdue",
            name="Overdue Patients",
            description="Patients with overdue care gap screenings",
            mimeType="application/json",
        ),
        Resource(
            uri="ehr://patients/active", 
            name="Active Patients",
            description="All active patients in the system",
            mimeType="application/json",
        ),
        Resource(
            uri="ehr://care-gaps/open",
            name="Open Care Gaps",
            description="All open care gaps requiring attention",
            mimeType="application/json",
        )
    ]


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available EHR tools"""
    return [
        Tool(
            name="get_overdue_patients",
            description="Get patients with overdue care gap screenings with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_age": {
                        "type": "integer",
                        "description": "Minimum patient age",
                        "minimum": 0,
                        "maximum": 150
                    },
                    "max_age": {
                        "type": "integer", 
                        "description": "Maximum patient age",
                        "minimum": 0,
                        "maximum": 150
                    },
                    "screening_type": {
                        "type": "string",
                        "description": "Type of screening (e.g., 'mammogram', 'colonoscopy', 'blood_pressure')"
                    },
                    "min_overdue_days": {
                        "type": "integer",
                        "description": "Minimum days overdue",
                        "minimum": 0
                    },
                    "max_overdue_days": {
                        "type": "integer",
                        "description": "Maximum days overdue", 
                        "minimum": 0
                    },
                    "priority_level": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Priority level filter"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 50
                    }
                },
                "additionalProperties": False
            }
        ),
        Tool(
            name="get_patient_details",
            description="Get detailed information for a specific patient",
            inputSchema={
                "type": "object",
                "properties": {
                    "patient_id": {
                        "type": "integer",
                        "description": "Patient ID",
                        "minimum": 1
                    }
                },
                "required": ["patient_id"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="update_patient_record",
            description="Update patient record information",
            inputSchema={
                "type": "object", 
                "properties": {
                    "patient_id": {
                        "type": "integer",
                        "description": "Patient ID",
                        "minimum": 1
                    },
                    "updates": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer", "minimum": 0, "maximum": 150},
                            "email": {"type": "string", "format": "email"},
                            "phone": {"type": "string"},
                            "insurance_info": {"type": "object"},
                            "risk_factors": {"type": "string"},
                            "preferred_contact_method": {
                                "type": "string",
                                "enum": ["email", "phone", "sms", "mail"]
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "required": ["patient_id", "updates"],
                "additionalProperties": False
            }
        ),
        Tool(
            name="close_care_gap", 
            description="Mark a care gap as closed/completed",
            inputSchema={
                "type": "object",
                "properties": {
                    "care_gap_id": {
                        "type": "integer",
                        "description": "Care gap ID",
                        "minimum": 1
                    },
                    "completion_date": {
                        "type": "string",
                        "format": "date",
                        "description": "Date when screening was completed (YYYY-MM-DD format)"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about the completion"
                    }
                },
                "required": ["care_gap_id"],
                "additionalProperties": False
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[types.TextContent]:
    """Handle tool calls"""
    try:
        if name == "get_overdue_patients":
            return await _get_overdue_patients(**arguments)
        elif name == "get_patient_details":
            return await _get_patient_details(**arguments)
        elif name == "update_patient_record":
            return await _update_patient_record(**arguments)
        elif name == "close_care_gap":
            return await _close_care_gap(**arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        security_manager.log_audit_event(
            event_type="tool_error",
            details={"tool": name, "error": str(e), "arguments": arguments}
        )
        return [types.TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def _get_overdue_patients(**kwargs) -> Sequence[types.TextContent]:
    """Get overdue patients with filters"""
    try:
        with get_db_session() as session:
            # Build query with filters
            query = session.query(Patient).join(CareGap).filter(
                CareGap.status == CareGapStatus.OPEN,
                CareGap.overdue_days > 0
            )
            
            # Apply filters
            if "min_age" in kwargs and "max_age" in kwargs:
                if not data_validator.validate_age_range(kwargs["min_age"], kwargs["max_age"]):
                    raise ValueError("Invalid age range")
                query = query.filter(and_(
                    Patient.age >= kwargs["min_age"],
                    Patient.age <= kwargs["max_age"]
                ))
            elif "min_age" in kwargs:
                query = query.filter(Patient.age >= kwargs["min_age"])
            elif "max_age" in kwargs:
                query = query.filter(Patient.age <= kwargs["max_age"])
            
            if "screening_type" in kwargs:
                query = query.filter(CareGap.screening_type.ilike(f"%{kwargs['screening_type']}%"))
            
            if "min_overdue_days" in kwargs:
                query = query.filter(CareGap.overdue_days >= kwargs["min_overdue_days"])
            
            if "max_overdue_days" in kwargs:
                query = query.filter(CareGap.overdue_days <= kwargs["max_overdue_days"])
            
            if "priority_level" in kwargs:
                try:
                    priority = PriorityLevel(kwargs["priority_level"])
                    query = query.filter(CareGap.priority_level == priority)
                except ValueError:
                    raise ValueError(f"Invalid priority level: {kwargs['priority_level']}")
            
            # Apply limit
            limit = kwargs.get("limit", 50)
            query = query.limit(limit)
            
            # Execute query with eager loading
            patients = query.options(
                joinedload(Patient.care_gaps)
            ).distinct().all()
            
            # Prepare results
            results = []
            for patient in patients:
                overdue_gaps = [
                    {
                        "care_gap_id": gap.id,
                        "screening_type": gap.screening_type,
                        "overdue_days": gap.overdue_days,
                        "priority_level": gap.priority_level.value,
                        "last_screening_date": gap.last_screening_date.isoformat() if gap.last_screening_date else None
                    }
                    for gap in patient.care_gaps 
                    if gap.status == CareGapStatus.OPEN and gap.overdue_days > 0
                ]
                
                if overdue_gaps:  # Only include patients with actual overdue gaps
                    results.append({
                        "patient_id": patient.id,
                        "name": patient.name,
                        "age": patient.age,
                        "email": patient.email,
                        "phone": patient.phone,
                        "preferred_contact_method": patient.preferred_contact_method,
                        "overdue_care_gaps": overdue_gaps,
                        "total_overdue_gaps": len(overdue_gaps)
                    })
            
            # Log audit event
            security_manager.log_audit_event(
                event_type="query_overdue_patients",
                details={
                    "filters": kwargs,
                    "results_count": len(results)
                }
            )
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "total_patients": len(results),
                    "filters_applied": kwargs,
                    "patients": results
                }, indent=2, default=str)
            )]
            
    except Exception as e:
        logger.error(f"Failed to get overdue patients: {e}")
        raise


async def _get_patient_details(patient_id: int, **kwargs) -> Sequence[types.TextContent]:
    """Get detailed patient information"""
    try:
        with get_db_session() as session:
            patient = session.query(Patient).options(
                joinedload(Patient.care_gaps),
                joinedload(Patient.appointments)
            ).filter(Patient.id == patient_id).first()
            
            if not patient:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "message": f"Patient with ID {patient_id} not found"
                    })
                )]
            
            # Prepare detailed patient information
            care_gaps_info = []
            for gap in patient.care_gaps:
                care_gaps_info.append({
                    "care_gap_id": gap.id,
                    "screening_type": gap.screening_type,
                    "last_screening_date": gap.last_screening_date.isoformat() if gap.last_screening_date else None,
                    "overdue_days": gap.overdue_days,
                    "priority_level": gap.priority_level.value,
                    "status": gap.status.value,
                    "created_at": gap.created_at.isoformat(),
                    "updated_at": gap.updated_at.isoformat()
                })
            
            appointments_info = []
            for apt in patient.appointments:
                appointments_info.append({
                    "appointment_id": apt.id,
                    "appointment_date": apt.appointment_date.isoformat(),
                    "doctor_name": apt.doctor_name,
                    "location": apt.location,
                    "status": apt.status.value,
                    "confirmation_code": apt.confirmation_code,
                    "created_at": apt.created_at.isoformat(),
                    "updated_at": apt.updated_at.isoformat()
                })
            
            patient_details = {
                "patient_id": patient.id,
                "name": patient.name,
                "age": patient.age,
                "email": patient.email,
                "phone": patient.phone,
                "date_of_birth": patient.date_of_birth.isoformat(),
                "insurance_info": patient.insurance_info,
                "risk_factors": patient.risk_factors,
                "preferred_contact_method": patient.preferred_contact_method,
                "created_at": patient.created_at.isoformat(),
                "updated_at": patient.updated_at.isoformat(),
                "care_gaps": care_gaps_info,
                "appointments": appointments_info,
                "total_care_gaps": len(care_gaps_info),
                "open_care_gaps": len([g for g in care_gaps_info if g["status"] == "open"]),
                "total_appointments": len(appointments_info)
            }
            
            # Log audit event
            security_manager.log_audit_event(
                event_type="patient_details_accessed",
                patient_id=patient_id,
                details={"accessed_fields": list(patient_details.keys())}
            )
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "patient": patient_details
                }, indent=2, default=str)
            )]
            
    except Exception as e:
        logger.error(f"Failed to get patient details for ID {patient_id}: {e}")
        raise


async def _update_patient_record(patient_id: int, updates: Dict[str, Any], **kwargs) -> Sequence[types.TextContent]:
    """Update patient record"""
    try:
        # Validate and sanitize updates
        sanitized_updates = data_validator.sanitize_patient_data(updates)
        
        if not sanitized_updates:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "error",
                    "message": "No valid updates provided"
                })
            )]
        
        with get_db_session() as session:
            patient = session.query(Patient).filter(Patient.id == patient_id).first()
            
            if not patient:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "message": f"Patient with ID {patient_id} not found"
                    })
                )]
            
            # Store original values for audit
            original_values = {}
            updated_fields = []
            
            # Apply updates
            for field, value in sanitized_updates.items():
                if hasattr(patient, field):
                    original_values[field] = getattr(patient, field)
                    setattr(patient, field, value)
                    updated_fields.append(field)
            
            # Update timestamp
            patient.updated_at = datetime.utcnow()
            
            session.commit()
            
            # Log audit event
            security_manager.log_audit_event(
                event_type="patient_record_updated",
                patient_id=patient_id,
                details={
                    "updated_fields": updated_fields,
                    "original_values": {k: str(v) for k, v in original_values.items()}
                }
            )
            
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": f"Patient {patient_id} updated successfully",
                    "updated_fields": updated_fields,
                    "patient_id": patient_id
                }, indent=2)
            )]
            
    except Exception as e:
        logger.error(f"Failed to update patient {patient_id}: {e}")
        raise


async def _close_care_gap(care_gap_id: int, completion_date: Optional[str] = None, notes: Optional[str] = None, **kwargs) -> Sequence[types.TextContent]:
    """Close a care gap"""
    try:
        with get_db_session() as session:
            care_gap = session.query(CareGap).filter(CareGap.id == care_gap_id).first()
            
            if not care_gap:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "error",
                        "message": f"Care gap with ID {care_gap_id} not found"
                    })
                )]
            
            if care_gap.status == CareGapStatus.CLOSED:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "status": "warning",
                        "message": f"Care gap {care_gap_id} is already closed"
                    })
                )]
            
            # Parse completion date
            if completion_date:
                try:
                    completion_date_obj = datetime.strptime(completion_date, "%Y-%m-%d").date()
                except ValueError:
                    raise ValueError("Invalid date format. Use YYYY-MM-DD format.")
            else:
                completion_date_obj = date.today()
            
            # Update care gap
            original_status = care_gap.status.value
            care_gap.status = CareGapStatus.CLOSED
            care_gap.last_screening_date = completion_date_obj
            care_gap.overdue_days = 0
            care_gap.updated_at = datetime.utcnow()
            
            session.commit()
            
            # Log audit event
            security_manager.log_audit_event(
                event_type="care_gap_closed",
                patient_id=care_gap.patient_id,
                details={
                    "care_gap_id": care_gap_id,
                    "screening_type": care_gap.screening_type,
                    "completion_date": completion_date_obj.isoformat(),
                    "original_status": original_status,
                    "notes": notes
                }
            )
            
            return [types.TextContent(
                type="text", 
                text=json.dumps({
                    "status": "success",
                    "message": f"Care gap {care_gap_id} closed successfully",
                    "care_gap_id": care_gap_id,
                    "patient_id": care_gap.patient_id,
                    "screening_type": care_gap.screening_type,
                    "completion_date": completion_date_obj.isoformat(),
                    "notes": notes
                }, indent=2)
            )]
            
    except Exception as e:
        logger.error(f"Failed to close care gap {care_gap_id}: {e}")
        raise


async def main():
    """Main server entry point"""
    logger.info("Starting Healthcare EHR MCP Server...")
    
    # Test database connection
    if not test_database_connection():
        logger.error("Failed to connect to database. Exiting.")
        return
    
    # Initialize server
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializeResult(
                protocolVersion="2024-11-05",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
                serverInfo={
                    "name": settings.MCP_SERVER_NAME,
                    "version": settings.MCP_SERVER_VERSION,
                },
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())