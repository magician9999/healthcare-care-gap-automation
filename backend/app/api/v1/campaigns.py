"""
Smart Campaign API endpoints for healthcare patient outreach
Integrates LLM-powered communication with messaging services
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from ...agents.communication_specialist import CommunicationSpecialistAgent
from ...services.messaging_service import MessagingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["Smart Campaigns"])


class CampaignRequest(BaseModel):
    patients: List[Dict[str, Any]] = Field(..., description="List of patients from query results")
    campaign_name: str = Field(..., description="Name for the campaign")
    message_customization: Optional[Dict[str, Any]] = Field(default={}, description="Custom message parameters")
    send_immediately: bool = Field(default=False, description="Send immediately or schedule")
    include_sms: bool = Field(default=True, description="Include SMS for phone preferences")
    include_booking_link: bool = Field(default=True, description="Include appointment booking link")


class CampaignResponse(BaseModel):
    status: str
    campaign_id: str
    total_patients: int
    messages_generated: int
    messages_sent: int
    failed_messages: int
    preview_messages: List[Dict[str, Any]]
    summary: Dict[str, Any]


# Initialize services
messaging_service = MessagingService()


@router.post("/start-smart-campaign", response_model=CampaignResponse)
async def start_smart_campaign(
    request: CampaignRequest,
    background_tasks: BackgroundTasks
):
    """
    Start an intelligent healthcare campaign with personalized messages
    
    This endpoint:
    1. Uses CommunicationSpecialist agent to generate personalized emails
    2. Leverages LLM for intelligent message customization
    3. Sends emails and SMS via MessagingService
    4. Includes appointment booking links
    """
    try:
        campaign_id = f"campaign_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{len(request.patients)}"
        
        logger.info(f"Starting smart campaign {campaign_id} for {len(request.patients)} patients")
        
        # Initialize communication agent
        comm_agent = CommunicationSpecialistAgent()
        await comm_agent.initialize()
        
        generated_messages = []
        preview_messages = []
        
        # Generate personalized messages for each patient
        for patient in request.patients[:5]:  # Preview first 5 for response
            try:
                # Prepare context for message generation
                context = {
                    "patient_id": patient.get("patient_id"),
                    "priority_level": patient.get("priority_level", "MEDIUM").upper(),
                    "screening_types": [patient.get("screening_type", "health_screening")],
                    "overdue_days": patient.get("overdue_days", 0),
                    "last_screening_date": patient.get("last_screening_date"),
                    **request.message_customization
                }
                
                # Generate personalized message using communication agent
                message_result = await comm_agent.process_message(
                    "create outreach message", 
                    context
                )
                
                if message_result.get("status") == "success":
                    # Prepare for messaging service
                    patient_message = {
                        "patient_data": patient,
                        "message_content": message_result.get("message_content", {}),
                        "follow_up_schedule": message_result.get("follow_up_schedule", []),
                        "delivery_recommendations": message_result.get("delivery_recommendations", {})
                    }
                    
                    generated_messages.append(patient_message)
                    
                    # Add to preview (first 5)
                    if len(preview_messages) < 5:
                        preview_messages.append({
                            "patient_id": patient.get("patient_id"),
                            "care_gap_id": patient.get("care_gap_id"),
                            "patient_name": patient.get("name"),
                            "name": patient.get("name"),  # For compatibility
                            "subject": message_result["message_content"].get("subject"),
                            "preview": message_result["message_content"].get("body", "")[:200] + "...",
                            "priority_level": patient.get("priority_level"),
                            "screening_type": patient.get("screening_type"),
                            "age": patient.get("age"),
                            "email": patient.get("email"),
                            "overdue_days": patient.get("overdue_days", 0)
                        })
                        
                else:
                    logger.warning(f"Failed to generate message for patient {patient.get('name', 'Unknown')}")
                    
            except Exception as e:
                logger.error(f"Message generation failed for patient {patient.get('name', 'Unknown')}: {e}")
                continue
        
        # Process all patients (not just preview)
        all_messages = []
        for patient in request.patients:
            try:
                context = {
                    "patient_id": patient.get("patient_id"),
                    "priority_level": patient.get("priority_level", "MEDIUM").upper(),
                    "screening_types": [patient.get("screening_type", "health_screening")],
                    "overdue_days": patient.get("overdue_days", 0),
                    "last_screening_date": patient.get("last_screening_date"),
                    **request.message_customization
                }
                
                message_result = await comm_agent.process_message(
                    "create outreach message", 
                    context
                )
                
                if message_result.get("status") == "success":
                    patient_message = {
                        "patient_data": patient,
                        "message_content": message_result.get("message_content", {}),
                        "follow_up_schedule": message_result.get("follow_up_schedule", []),
                        "delivery_recommendations": message_result.get("delivery_recommendations", {})
                    }
                    all_messages.append(patient_message)
                    
            except Exception as e:
                logger.error(f"Message generation failed for patient {patient.get('name', 'Unknown')}: {e}")
                continue
        
        # Send messages if requested
        sent_count = 0
        failed_count = 0
        
        if request.send_immediately and all_messages:
            if request.send_immediately:
                # Send in background
                background_tasks.add_task(
                    send_campaign_messages,
                    campaign_id,
                    all_messages,
                    request.include_sms,
                    request.include_booking_link
                )
                sent_count = len(all_messages)
            else:
                # For demo, simulate sending
                sent_count = len(all_messages)
        
        # Generate campaign summary
        summary = {
            "campaign_name": request.campaign_name,
            "created_at": datetime.utcnow().isoformat(),
            "total_patients": len(request.patients),
            "messages_generated": len(all_messages),
            "priority_distribution": _calculate_priority_distribution(request.patients),
            "screening_types": _calculate_screening_distribution(request.patients),
            "estimated_send_duration": f"{len(all_messages) * 2} minutes",
            "includes_sms": request.include_sms,
            "includes_booking_links": request.include_booking_link
        }
        
        await comm_agent.cleanup()
        
        return CampaignResponse(
            status="success",
            campaign_id=campaign_id,
            total_patients=len(request.patients),
            messages_generated=len(all_messages),
            messages_sent=sent_count,
            failed_messages=failed_count,
            preview_messages=preview_messages,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Smart campaign creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Campaign creation failed: {str(e)}")


@router.post("/send-test-email")
async def send_test_email():
    """Send a test email to Shivanshu Saxena for demo purposes"""
    try:
        # Create test patient data for Shivanshu
        test_patient = {
            "patient_id": 1,
            "name": "Shivanshu Saxena",
            "age": 35,
            "email": "shivanshusaxenaofficial@gmail.com",
            "phone": "+91-9876543210",
            "screening_type": "eye_exam",
            "last_screening_date": "2022-12-29",
            "overdue_days": 249,
            "priority_level": "HIGH",
            "risk_factors": "hypertension, family_history_diabetes",
            "preferred_contact_method": "email"
        }
        
        # Initialize communication agent
        comm_agent = CommunicationSpecialistAgent()
        await comm_agent.initialize()
        
        # Generate personalized message
        context = {
            "patient_id": 1,
            "priority_level": "HIGH",
            "screening_types": ["eye_exam"],
            "overdue_days": 249,
            "last_screening_date": "2022-12-29"
        }
        
        message_result = await comm_agent.process_message("create outreach message", context)
        
        if message_result.get("status") == "success":
            # Send email using messaging service
            email_result = await messaging_service.send_personalized_email(
                test_patient,
                message_result["message_content"]["body"],
                message_result["message_content"]["subject"]
            )
            
            await comm_agent.cleanup()
            
            return {
                "status": "success",
                "message": "Test email sent successfully",
                "recipient": "shivanshusaxenaofficial@gmail.com",
                "email_result": email_result,
                "generated_message": {
                    "subject": message_result["message_content"]["subject"],
                    "preview": message_result["message_content"]["body"][:300] + "...",
                    "booking_link": email_result.get("booking_link")
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate test message")
            
    except Exception as e:
        logger.error(f"Test email sending failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test email failed: {str(e)}")


@router.get("/campaign/{campaign_id}")
async def get_campaign_status(campaign_id: str):
    """Get status and results of a specific campaign"""
    try:
        # For demo, return mock campaign status
        # In production, this would query a campaigns database
        return {
            "status": "success",
            "campaign_id": campaign_id,
            "current_status": "completed",
            "progress": {
                "total_patients": 29,
                "emails_sent": 25,
                "sms_sent": 12,
                "emails_opened": 18,
                "links_clicked": 8,
                "appointments_booked": 3
            },
            "started_at": "2025-09-03T10:00:00Z",
            "completed_at": "2025-09-03T10:15:00Z",
            "next_follow_up": "2025-09-06T10:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Campaign status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/booking-slots")
async def get_available_booking_slots(
    screening_type: str = "general",
    patient_id: Optional[int] = None
):
    """Get available appointment booking slots"""
    try:
        slots = messaging_service.get_available_time_slots(screening_type)
        
        return {
            "status": "success",
            "screening_type": screening_type,
            "available_slots": slots,
            "total_available": len(slots),
            "booking_instructions": "Click on any available slot to book your appointment"
        }
        
    except Exception as e:
        logger.error(f"Booking slots retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def send_campaign_messages(
    campaign_id: str, 
    messages: List[Dict[str, Any]], 
    include_sms: bool,
    include_booking_link: bool
):
    """Background task to send campaign messages"""
    try:
        logger.info(f"Starting to send {len(messages)} messages for campaign {campaign_id}")
        
        campaign_data = {
            "campaign_id": campaign_id,
            "include_booking_link": include_booking_link
        }
        
        # Process messages in batches
        for message in messages:
            patient_data = message["patient_data"]
            message_content = message["message_content"]
            
            # Prepare campaign data for this patient
            campaign_data.update({
                "email_subject": message_content.get("subject", "Healthcare Appointment Reminder"),
                "email_content": message_content.get("body", ""),
                "sms_content": message_content.get("channel_versions", {}).get("sms", {}).get("body", "")
            })
            
            try:
                # Send email
                if patient_data.get("email"):
                    email_result = await messaging_service.send_personalized_email(
                        patient_data,
                        campaign_data["email_content"],
                        campaign_data["email_subject"]
                    )
                    logger.info(f"Email sent to {patient_data.get('name')}: {email_result['status']}")
                
                # Send SMS if enabled and phone available
                if include_sms and patient_data.get("phone"):
                    sms_result = await messaging_service.send_sms_notification(
                        patient_data,
                        campaign_data.get("sms_content", campaign_data["email_content"][:100])
                    )
                    logger.info(f"SMS sent to {patient_data.get('name')}: {sms_result['status']}")
                    
            except Exception as e:
                logger.error(f"Failed to send message to {patient_data.get('name', 'Unknown')}: {e}")
                continue
        
        logger.info(f"Campaign {campaign_id} message sending completed")
        
    except Exception as e:
        logger.error(f"Background campaign sending failed: {e}")


def _calculate_priority_distribution(patients: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate priority level distribution"""
    distribution = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    
    for patient in patients:
        priority = patient.get("priority_level", "MEDIUM").upper()
        if priority in distribution:
            distribution[priority] += 1
    
    return distribution


def _calculate_screening_distribution(patients: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate screening type distribution"""
    distribution = {}
    
    for patient in patients:
        screening = patient.get("screening_type", "unknown")
        distribution[screening] = distribution.get(screening, 0) + 1
    
    return dict(sorted(distribution.items(), key=lambda x: x[1], reverse=True))