import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import re

from .base_agent import BaseHealthcareAgent

logger = logging.getLogger(__name__)


class CommunicationSpecialistAgent(BaseHealthcareAgent):
    """
    Specialized AutoGen agent for crafting personalized patient outreach messages
    Creates tailored communications based on patient demographics, history, and urgency
    """
    
    def __init__(self):
        system_message = """You are a Healthcare Communication Specialist AI with expertise in patient outreach and engagement.
        Your role is to:
        1. Craft personalized patient outreach messages based on demographics and medical history
        2. Adapt communication style based on urgency, risk level, and patient preferences
        3. Create follow-up communication strategies and schedules
        4. Ensure messages are empathetic, clear, and actionable
        5. Consider health literacy and cultural sensitivity
        
        You have access to patient data through MCP tools and create communications that drive patient engagement
        while maintaining professional healthcare communication standards."""
        
        super().__init__(
            name="CommunicationSpecialistAgent",
            role="Healthcare Communication Specialist",
            system_message=system_message
        )
        
        # Communication templates by urgency and screening type
        self.message_templates = {
            "CRITICAL": {
                "subject": "URGENT: Important Health Screening Required - Action Needed",
                "tone": "urgent but caring",
                "opening": "We're reaching out because your health records show you're significantly overdue for an important health screening.",
                "call_to_action": "Please call us within 24 hours to schedule your appointment."
            },
            "HIGH": {
                "subject": "Important: Time for Your {screening_type} - Priority Scheduling Available",
                "tone": "concerned but reassuring",
                "opening": "Our records show it's time for your {screening_type}, and we want to help you stay on track with your preventive care.",
                "call_to_action": "Please call us within 48 hours to schedule at your convenience."
            },
            "MEDIUM": {
                "subject": "Gentle Reminder: {screening_type} Due - Let's Keep You Healthy",
                "tone": "friendly and supportive",
                "opening": "We hope you're doing well! This is a friendly reminder that you're due for your {screening_type}.",
                "call_to_action": "Please call us within the next week to schedule your appointment."
            },
            "LOW": {
                "subject": "Health Reminder: {screening_type} Scheduling Available",
                "tone": "informative and encouraging",
                "opening": "As part of your ongoing preventive care, we wanted to remind you about your upcoming {screening_type}.",
                "call_to_action": "When convenient, please contact us to schedule your appointment."
            }
        }
        
        # Screening-specific messaging
        self.screening_messages = {
            "mammogram": {
                "importance": "Early detection of breast cancer can save lives and improve treatment outcomes.",
                "preparation": "The procedure takes about 20 minutes, and we'll make sure you're comfortable throughout.",
                "frequency": "Annual mammograms are recommended for women over 40."
            },
            "colonoscopy": {
                "importance": "Colonoscopy screening can prevent colorectal cancer by detecting and removing precancerous polyps.",
                "preparation": "We'll provide detailed preparation instructions to ensure the most effective screening.",
                "frequency": "Most people need this screening every 10 years starting at age 45."
            },
            "blood_pressure_check": {
                "importance": "Regular blood pressure monitoring helps prevent heart disease and stroke.",
                "preparation": "This quick, painless check can be done during a regular office visit.",
                "frequency": "We recommend checking blood pressure at least annually, or more frequently if you have risk factors."
            },
            "diabetes_screening": {
                "importance": "Early detection of diabetes or prediabetes allows for better management and prevention of complications.",
                "preparation": "This simple blood test helps us monitor your metabolic health.",
                "frequency": "Adults should be screened every 3 years, or more often if at higher risk."
            }
        }
        
        # Communication preferences by contact method
        self.channel_preferences = {
            "email": {"format": "detailed", "length": "medium", "links": True},
            "phone": {"format": "conversational", "length": "brief", "scripts": True},
            "sms": {"format": "concise", "length": "short", "urgent_only": True},
            "mail": {"format": "formal", "length": "detailed", "branding": True}
        }
    
    async def process_message(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process communication requests"""
        self.add_to_conversation("user", message, context)
        
        try:
            request_type = self._parse_communication_request(message)
            
            if request_type == "create_outreach_message":
                result = await self._create_outreach_message(context or {})
            elif request_type == "create_follow_up_sequence":
                result = await self._create_follow_up_sequence(context or {})
            elif request_type == "personalize_message":
                result = await self._personalize_message(context or {})
            elif request_type == "batch_communications":
                result = await self._create_batch_communications(context or {})
            else:
                result = await self._general_communication_guidance(message, context or {})
            
            self.add_to_conversation("assistant", json.dumps(result), {"request_type": request_type})
            return result
            
        except Exception as e:
            logger.error(f"CommunicationSpecialistAgent processing failed: {e}")
            error_result = {
                "status": "error",
                "message": f"Communication generation failed: {str(e)}",
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.add_to_conversation("assistant", json.dumps(error_result), {"error": True})
            return error_result
    
    def _parse_communication_request(self, message: str) -> str:
        """Parse the type of communication request"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ["outreach", "message", "contact"]):
            return "create_outreach_message"
        elif any(keyword in message_lower for keyword in ["follow up", "sequence", "series"]):
            return "create_follow_up_sequence"
        elif any(keyword in message_lower for keyword in ["personalize", "customize", "tailor"]):
            return "personalize_message"
        elif any(keyword in message_lower for keyword in ["batch", "bulk", "multiple"]):
            return "batch_communications"
        else:
            return "general_communication"
    
    async def _create_outreach_message(self, context: Dict) -> Dict[str, Any]:
        """Create personalized outreach message for a patient"""
        try:
            # Get patient information
            patient_id = context.get("patient_id")
            priority_level = context.get("priority_level", "MEDIUM")
            screening_types = context.get("screening_types", [])
            
            if not patient_id:
                # Check if this is a batch communication request (no patient_id provided)
                batch_patients = context.get("prioritized_patients", [])
                if not batch_patients:
                    return {
                        "status": "success",
                        "message": "No patients available for outreach creation", 
                        "communications": [],
                        "total_created": 0,
                        "agent": self.name
                    }
                else:
                    # Handle batch communication
                    return await self._create_batch_communications(context)
            
            # Get detailed patient information
            patient_details = await self.mcp_client.get_patient_details(patient_id)
            
            if patient_details.get("status") != "success":
                return {
                    "status": "error", 
                    "message": f"Failed to retrieve patient details: {patient_details.get('message')}",
                    "agent": self.name
                }
            
            patient = patient_details["patient"]
            
            # Generate personalized message
            message_content = self._generate_personalized_message(
                patient, priority_level, screening_types, context
            )
            
            # Create follow-up schedule
            follow_up_schedule = self._create_follow_up_schedule(priority_level, patient)
            
            return {
                "status": "success",
                "message_type": "personalized_outreach",
                "patient_id": patient_id,
                "patient_name": patient["name"],
                "priority_level": priority_level,
                "message_content": message_content,
                "follow_up_schedule": follow_up_schedule,
                "delivery_recommendations": self._get_delivery_recommendations(patient),
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Outreach message creation failed: {e}")
            raise
    
    def _generate_personalized_message(self, patient: Dict, priority_level: str, 
                                     screening_types: List[str], context: Dict) -> Dict[str, Any]:
        """Generate personalized message content"""
        
        # Get patient info
        name = patient["name"].split()[0]  # First name for personalization
        age = patient["age"]
        preferred_contact = patient.get("preferred_contact_method", "email")
        care_gaps = patient.get("care_gaps", [])
        overdue_gaps = [gap for gap in care_gaps if gap.get("status") == "open"]
        
        # Determine primary screening type
        if screening_types:
            primary_screening = screening_types[0]
        elif overdue_gaps:
            primary_screening = overdue_gaps[0].get("screening_type", "health screening")
        else:
            primary_screening = "health screening"
        
        # Get template for priority level
        template = self.message_templates.get(priority_level, self.message_templates["MEDIUM"])
        
        # Personalize subject line
        subject = template["subject"].format(screening_type=primary_screening.replace("_", " ").title())
        
        # Generate message body
        greeting = f"Dear {name},"
        
        # Opening based on priority and personal touch
        opening = template["opening"].format(screening_type=primary_screening.replace("_", " "))
        
        # Add age-appropriate context
        if age >= 65:
            age_context = f"As someone who's {age}, staying current with preventive screenings is especially important for maintaining your health and independence."
        elif age >= 50:
            age_context = f"At {age}, preventive care becomes increasingly important for early detection and maintaining optimal health."
        else:
            age_context = "Preventive screenings are one of the best investments you can make in your long-term health."
        
        # Add screening-specific information
        screening_info = self.screening_messages.get(primary_screening, {})
        importance = screening_info.get("importance", "This screening is an important part of your preventive healthcare.")
        preparation = screening_info.get("preparation", "Our staff will help guide you through the process.")
        
        # Risk factors consideration
        risk_factors = patient.get("risk_factors", "")
        risk_message = ""
        if risk_factors and any(risk in risk_factors.lower() for risk in ["family history", "smoking", "diabetes"]):
            risk_message = "Given your health history, staying current with this screening is particularly important."
        
        # Create urgency-appropriate body
        if priority_level == "CRITICAL":
            urgency_message = "This screening is significantly overdue, and we're concerned about your health. "
            next_steps = f"Please call us immediately at [PHONE] or reply to this message. We have priority appointments available."
        elif priority_level == "HIGH":
            urgency_message = "This screening is past due, and we want to help you get back on track quickly. "
            next_steps = f"Please call us at [PHONE] within the next 2 days. We have flexible scheduling options available."
        else:
            urgency_message = ""
            next_steps = f"Please call us at [PHONE] at your convenience, or use our online scheduling portal at [PORTAL_LINK]."
        
        # Assemble message
        body_parts = [
            greeting,
            "",
            opening,
            "",
            age_context,
            "",
            importance,
            risk_message,
            "",
            urgency_message + preparation,
            "",
            next_steps,
            "",
            "We're here to support your health journey and answer any questions you may have.",
            "",
            "Best regards,",
            "[CARE_TEAM_NAME]",
            "[CLINIC_NAME]",
            "[PHONE] | [EMAIL]"
        ]
        
        # Filter out empty strings and join
        message_body = "\n".join([part for part in body_parts if part])
        
        # Create channel-specific versions
        channel_versions = self._adapt_message_for_channels(
            subject, message_body, preferred_contact, priority_level
        )
        
        return {
            "subject": subject,
            "body": message_body,
            "tone": template["tone"],
            "priority_level": priority_level,
            "personalization_elements": {
                "name": name,
                "age": age,
                "primary_screening": primary_screening,
                "has_risk_factors": bool(risk_factors),
                "overdue_count": len(overdue_gaps)
            },
            "channel_versions": channel_versions,
            "estimated_reading_level": self._estimate_reading_level(message_body)
        }
    
    def _adapt_message_for_channels(self, subject: str, body: str, preferred_channel: str, priority_level: str) -> Dict[str, Any]:
        """Adapt message for different communication channels"""
        
        channel_versions = {}
        
        # Email version (full message)
        channel_versions["email"] = {
            "subject": subject,
            "body": body,
            "format": "html_and_text",
            "attachments": ["screening_info_brochure.pdf"] if priority_level in ["HIGH", "CRITICAL"] else []
        }
        
        # SMS version (condensed)
        if priority_level in ["HIGH", "CRITICAL"]:
            sms_body = f"URGENT: {subject.split(':')[1].strip()} Call [PHONE] ASAP to schedule. -[CLINIC_NAME]"
        else:
            sms_body = f"Reminder: Time for your health screening. Call [PHONE] to schedule. -[CLINIC_NAME]"
        
        channel_versions["sms"] = {
            "body": sms_body,
            "character_count": len(sms_body),
            "estimated_segments": (len(sms_body) // 160) + 1
        }
        
        # Phone script
        phone_script = f"""
        Hello, this is [CALLER_NAME] from [CLINIC_NAME]. 
        May I speak with [PATIENT_NAME]?
        
        I'm calling because our records show you're due for your {subject.split()[-1] if 'screening' in subject.lower() else 'health screening'}.
        
        {'This is quite urgent and' if priority_level == 'CRITICAL' else 'We'} would like to help you schedule this at your earliest convenience.
        
        Do you have a few minutes to schedule this now, or would you prefer I call back at a better time?
        """
        
        channel_versions["phone"] = {
            "script": phone_script.strip(),
            "estimated_duration": "2-3 minutes",
            "key_points": [
                "Confirm patient identity",
                f"Explain {priority_level.lower()} priority level",
                "Offer scheduling options",
                "Address any concerns"
            ]
        }
        
        # Mail version (formal)
        mail_header = "[CLINIC_LETTERHEAD]\n[DATE]\n\n[PATIENT_NAME]\n[PATIENT_ADDRESS]\n\n"
        mail_body = mail_header + body.replace("[PHONE]", "[CLINIC_PHONE]").replace("[EMAIL]", "[CLINIC_EMAIL]")
        
        channel_versions["mail"] = {
            "body": mail_body,
            "includes_branding": True,
            "envelope_priority": "Priority Mail" if priority_level == "CRITICAL" else "Standard"
        }
        
        return channel_versions
    
    def _create_follow_up_schedule(self, priority_level: str, patient: Dict) -> List[Dict[str, Any]]:
        """Create follow-up communication schedule"""
        
        preferred_contact = patient.get("preferred_contact_method", "email")
        
        if priority_level == "CRITICAL":
            follow_ups = [
                {"days_after": 1, "method": "phone", "message": "Urgent follow-up call if no response"},
                {"days_after": 2, "method": preferred_contact, "message": "Second urgent outreach"},
                {"days_after": 4, "method": "phone", "message": "Final urgent attempt with care team escalation"}
            ]
        elif priority_level == "HIGH":
            follow_ups = [
                {"days_after": 3, "method": preferred_contact, "message": "Friendly reminder with scheduling assistance"},
                {"days_after": 7, "method": "phone", "message": "Personal follow-up call"},
                {"days_after": 14, "method": preferred_contact, "message": "Final reminder with alternative options"}
            ]
        elif priority_level == "MEDIUM":
            follow_ups = [
                {"days_after": 7, "method": preferred_contact, "message": "Gentle reminder"},
                {"days_after": 21, "method": preferred_contact, "message": "Second reminder with health education"},
                {"days_after": 42, "method": "phone", "message": "Check-in call to address barriers"}
            ]
        else:  # LOW
            follow_ups = [
                {"days_after": 14, "method": preferred_contact, "message": "Friendly reminder"},
                {"days_after": 60, "method": preferred_contact, "message": "Quarterly health reminder"}
            ]
        
        # Add actual dates
        today = date.today()
        for follow_up in follow_ups:
            follow_up_date = today + timedelta(days=follow_up["days_after"])
            follow_up["scheduled_date"] = follow_up_date.isoformat()
        
        return follow_ups
    
    def _get_delivery_recommendations(self, patient: Dict) -> Dict[str, Any]:
        """Get recommendations for message delivery"""
        
        preferred_contact = patient.get("preferred_contact_method", "email")
        age = patient.get("age", 0)
        
        # Age-based delivery preferences
        if age >= 70:
            recommended_channels = ["phone", "mail", "email"]
            avoid_channels = ["sms"]
        elif age >= 50:
            recommended_channels = ["email", "phone", "mail"]
            avoid_channels = []
        else:
            recommended_channels = ["email", "sms", "phone"]
            avoid_channels = ["mail"]
        
        # Timing recommendations
        if age >= 65:
            best_times = ["9:00 AM - 11:00 AM", "2:00 PM - 4:00 PM"]
        else:
            best_times = ["8:00 AM - 10:00 AM", "5:00 PM - 7:00 PM"]
        
        return {
            "primary_channel": preferred_contact,
            "recommended_channels": recommended_channels,
            "avoid_channels": avoid_channels,
            "best_contact_times": best_times,
            "frequency_limit": "No more than 2 contacts per week",
            "special_considerations": self._get_special_considerations(patient)
        }
    
    def _get_special_considerations(self, patient: Dict) -> List[str]:
        """Get special considerations for patient communication"""
        considerations = []
        
        age = patient.get("age", 0)
        risk_factors = patient.get("risk_factors", "") or ""
        
        if age >= 75:
            considerations.append("May benefit from slower-paced phone conversations")
            considerations.append("Consider involving family members in communications")
        
        if "hearing" in risk_factors.lower():
            considerations.append("Phone calls may not be effective - prefer written communication")
        
        if any(condition in risk_factors.lower() for condition in ["anxiety", "depression"]):
            considerations.append("Use reassuring, supportive tone and emphasize care team support")
        
        if "language" in patient.get("notes", "").lower():
            considerations.append("May require translation services or multilingual materials")
        
        return considerations
    
    def _estimate_reading_level(self, text: str) -> str:
        """Estimate reading level of message (simplified)"""
        
        sentences = len(re.findall(r'[.!?]+', text))
        words = len(text.split())
        
        if sentences == 0:
            return "Unable to determine"
        
        avg_sentence_length = words / sentences
        
        if avg_sentence_length < 10:
            return "Elementary (5th-6th grade)"
        elif avg_sentence_length < 15:
            return "Middle School (7th-8th grade)"
        elif avg_sentence_length < 20:
            return "High School (9th-12th grade)"
        else:
            return "College Level"
    
    async def _create_follow_up_sequence(self, context: Dict) -> Dict[str, Any]:
        """Create a sequence of follow-up messages"""
        patient_id = context.get("patient_id")
        sequence_type = context.get("sequence_type", "standard")
        
        if not patient_id:
            return {
                "status": "error",
                "message": "Patient ID required for follow-up sequence",
                "agent": self.name
            }
        
        # This would create a multi-message sequence
        # For now, create a basic follow-up schedule
        patient_details = await self.mcp_client.get_patient_details(patient_id)
        
        if patient_details.get("status") != "success":
            return {
                "status": "error",
                "message": f"Failed to retrieve patient details: {patient_details.get('message')}",
                "agent": self.name
            }
        
        patient = patient_details["patient"]
        priority_level = context.get("priority_level", "MEDIUM")
        
        follow_up_schedule = self._create_follow_up_schedule(priority_level, patient)
        
        return {
            "status": "success",
            "sequence_type": sequence_type,
            "patient_id": patient_id,
            "follow_up_schedule": follow_up_schedule,
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _personalize_message(self, context: Dict) -> Dict[str, Any]:
        """Personalize an existing message template"""
        # Implementation for message personalization
        return await self._create_outreach_message(context)
    
    async def _create_batch_communications(self, context: Dict) -> Dict[str, Any]:
        """Create communications for multiple patients"""
        patient_list = context.get("patients", [])
        
        if not patient_list:
            return {
                "status": "error",
                "message": "Patient list required for batch communications",
                "agent": self.name
            }
        
        batch_results = []
        
        for patient_info in patient_list:
            try:
                patient_context = {
                    "patient_id": patient_info.get("patient_id"),
                    "priority_level": patient_info.get("priority_level", "MEDIUM"),
                    "screening_types": patient_info.get("screening_types", [])
                }
                
                message_result = await self._create_outreach_message(patient_context)
                batch_results.append(message_result)
                
            except Exception as e:
                batch_results.append({
                    "status": "error",
                    "patient_id": patient_info.get("patient_id"),
                    "message": str(e)
                })
        
        return {
            "status": "success",
            "batch_type": "outreach_messages",
            "total_patients": len(patient_list),
            "successful_messages": len([r for r in batch_results if r.get("status") == "success"]),
            "failed_messages": len([r for r in batch_results if r.get("status") == "error"]),
            "results": batch_results,
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _general_communication_guidance(self, message: str, context: Dict) -> Dict[str, Any]:
        """Provide general communication guidance"""
        return {
            "status": "info",
            "message": "I specialize in creating personalized patient outreach communications. Please specify: 'create outreach message', 'follow-up sequence', or 'batch communications'",
            "available_functions": [
                "create_outreach_message",
                "create_follow_up_sequence",
                "personalize_message",
                "batch_communications"
            ],
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }