"""
Messaging Service for Healthcare Campaign Management
Handles email and SMS communication with SMTP and SMS integration
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os
import json
import requests
from jinja2 import Template

from ..config.settings import settings

logger = logging.getLogger(__name__)


class MessagingService:
    """Service for sending emails and SMS messages for healthcare campaigns"""
    
    def __init__(self):
        # Email configuration
        self.smtp_server = getattr(settings, 'SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_username = getattr(settings, 'SMTP_USERNAME', 'shivanshusaxenaofficial@gmail.com')
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', 'your-app-password')
        self.from_email = getattr(settings, 'FROM_EMAIL', 'shivanshusaxenaofficial@gmail.com')
        
        # SMS configuration (using Twilio for demo)
        self.twilio_account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        self.twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        self.twilio_phone_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        
        # Booking system configuration
        self.booking_base_url = getattr(settings, 'BOOKING_BASE_URL', 'http://localhost:8000')
    
    async def send_personalized_email(self, patient_data: Dict[str, Any], email_content: str, subject: str) -> Dict[str, Any]:
        """Send personalized email to patient with booking link"""
        try:
            # Create booking link
            booking_link = self._generate_booking_link(patient_data)
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = patient_data.get('email', '')
            
            # Create HTML email with booking button
            html_content = self._create_html_email_template(
                patient_data, 
                email_content, 
                booking_link
            )
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email via SMTP
            success = await self._send_via_smtp(msg, patient_data.get('email'))
            
            if success:
                return {
                    "status": "success",
                    "message": f"Email sent successfully to {patient_data.get('name')}",
                    "email": patient_data.get('email'),
                    "booking_link": booking_link,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to send email to {patient_data.get('name')}",
                    "email": patient_data.get('email')
                }
                
        except Exception as e:
            logger.error(f"Email sending failed for {patient_data.get('name', 'Unknown')}: {e}")
            return {
                "status": "error",
                "message": f"Email sending failed: {str(e)}",
                "email": patient_data.get('email', '')
            }
    
    async def send_sms_notification(self, patient_data: Dict[str, Any], message_content: str) -> Dict[str, Any]:
        """Send SMS notification to patient"""
        try:
            phone_number = patient_data.get('phone', '')
            if not phone_number:
                return {
                    "status": "error",
                    "message": "No phone number available for patient",
                    "patient": patient_data.get('name', 'Unknown')
                }
            
            # For demo purposes, we'll simulate SMS sending
            # In production, integrate with Twilio, AWS SNS, or other SMS service
            
            booking_link = self._generate_booking_link(patient_data)
            sms_content = f"{message_content}\n\nBook your appointment: {booking_link}"
            
            # Simulate SMS sending (replace with actual SMS API)
            success = await self._send_via_sms_api(phone_number, sms_content)
            
            if success:
                return {
                    "status": "success",
                    "message": f"SMS sent successfully to {patient_data.get('name')}",
                    "phone": phone_number,
                    "booking_link": booking_link,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to send SMS to {patient_data.get('name')}",
                    "phone": phone_number
                }
                
        except Exception as e:
            logger.error(f"SMS sending failed for {patient_data.get('name', 'Unknown')}: {e}")
            return {
                "status": "error",
                "message": f"SMS sending failed: {str(e)}",
                "phone": patient_data.get('phone', '')
            }
    
    async def send_campaign_batch(self, patients: List[Dict[str, Any]], campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send campaign messages to a batch of patients"""
        results = {
            "campaign_id": campaign_data.get("campaign_id", f"campaign_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"),
            "total_patients": len(patients),
            "email_results": [],
            "sms_results": [],
            "summary": {
                "emails_sent": 0,
                "emails_failed": 0,
                "sms_sent": 0,
                "sms_failed": 0
            },
            "started_at": datetime.utcnow().isoformat()
        }
        
        for patient in patients:
            try:
                # Send email if email preference or email available
                preferred_contact = patient.get('preferred_contact_method', 'email').lower()
                
                if patient.get('email') and preferred_contact in ['email', 'both']:
                    email_result = await self.send_personalized_email(
                        patient, 
                        campaign_data.get('email_content', ''),
                        campaign_data.get('email_subject', 'Healthcare Appointment Reminder')
                    )
                    results["email_results"].append(email_result)
                    
                    if email_result["status"] == "success":
                        results["summary"]["emails_sent"] += 1
                    else:
                        results["summary"]["emails_failed"] += 1
                
                # Send SMS if SMS preference or phone available
                if patient.get('phone') and preferred_contact in ['sms', 'text', 'phone', 'both']:
                    sms_result = await self.send_sms_notification(
                        patient,
                        campaign_data.get('sms_content', campaign_data.get('email_content', ''))
                    )
                    results["sms_results"].append(sms_result)
                    
                    if sms_result["status"] == "success":
                        results["summary"]["sms_sent"] += 1
                    else:
                        results["summary"]["sms_failed"] += 1
                        
            except Exception as e:
                logger.error(f"Campaign sending failed for patient {patient.get('name', 'Unknown')}: {e}")
                results["email_results"].append({
                    "status": "error",
                    "message": f"Campaign processing failed: {str(e)}",
                    "patient": patient.get('name', 'Unknown')
                })
                results["summary"]["emails_failed"] += 1
        
        results["completed_at"] = datetime.utcnow().isoformat()
        return results
    
    def _generate_booking_link(self, patient_data: Dict[str, Any]) -> str:
        """Generate booking link for patient appointment"""
        patient_id = patient_data.get('patient_id', '')
        screening_type = patient_data.get('screening_type', 'general')
        
        # Create booking URL with patient context
        booking_url = f"{self.booking_base_url}/book-appointment"
        params = f"?patient_id={patient_id}&screening_type={screening_type}&utm_source=campaign"
        
        return booking_url + params
    
    def _create_html_email_template(self, patient_data: Dict[str, Any], content: str, booking_link: str) -> str:
        """Create HTML email template with booking button"""
        
        template_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Healthcare Appointment Reminder</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .email-container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #3b82f6;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #3b82f6;
            margin: 0;
        }
        .content {
            margin-bottom: 30px;
        }
        .booking-button {
            text-align: center;
            margin: 30px 0;
        }
        .btn {
            display: inline-block;
            background-color: #3b82f6;
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            font-size: 16px;
        }
        .btn:hover {
            background-color: #2563eb;
        }
        .patient-info {
            background-color: #f8fafc;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .footer {
            text-align: center;
            font-size: 12px;
            color: #666;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }
    </style>
</head>
<body>
    <div class="email-container">
        <div class="header">
            <h1>Healthcare Appointment Reminder</h1>
        </div>
        
        <div class="content">
            <p>Dear {{ patient_name }},</p>
            
            {{ email_content }}
            
            <div class="patient-info">
                <h3>Your Screening Details:</h3>
                <p><strong>Screening Type:</strong> {{ screening_type }}</p>
                <p><strong>Last Screening:</strong> {{ last_screening_date }}</p>
                <p><strong>Days Overdue:</strong> {{ overdue_days }}</p>
                <p><strong>Priority Level:</strong> {{ priority_level }}</p>
            </div>
        </div>
        
        <div class="booking-button">
            <a href="{{ booking_link }}" class="btn">Book Your Appointment Now</a>
        </div>
        
        <p>If you have any questions or concerns, please don't hesitate to contact our office.</p>
        
        <div class="footer">
            <p>This is an automated message from your healthcare provider.</p>
            <p>If you no longer wish to receive these reminders, please contact our office.</p>
        </div>
    </div>
</body>
</html>
        """
        
        template = Template(template_html)
        
        return template.render(
            patient_name=patient_data.get('name', 'Patient'),
            email_content=content,
            screening_type=patient_data.get('screening_type', 'Health Screening').replace('_', ' ').title(),
            last_screening_date=patient_data.get('last_screening_date', 'Not recorded'),
            overdue_days=patient_data.get('overdue_days', 0),
            priority_level=patient_data.get('priority_level', 'Medium').title(),
            booking_link=booking_link
        )
    
    async def _send_via_smtp(self, msg: MIMEMultipart, to_email: str) -> bool:
        """Send email via SMTP server"""
        try:
            # For demo purposes, we'll simulate email sending
            # In production, configure with real SMTP credentials
            
            logger.info(f"Demo: Would send email to {to_email}")
            logger.info(f"Subject: {msg['Subject']}")
            
            # Uncomment below for actual SMTP sending
            """
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            """
            
            # Simulate successful sending for demo
            return True
            
        except Exception as e:
            logger.error(f"SMTP sending failed: {e}")
            return False
    
    async def _send_via_sms_api(self, phone_number: str, message: str) -> bool:
        """Send SMS via API (Twilio simulation)"""
        try:
            # For demo purposes, simulate SMS sending
            logger.info(f"Demo: Would send SMS to {phone_number}")
            logger.info(f"Message: {message}")
            
            # Uncomment and configure for actual SMS sending via Twilio
            """
            from twilio.rest import Client
            
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            message = client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=phone_number
            )
            """
            
            # Simulate successful sending for demo
            return True
            
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return False
    
    def get_available_time_slots(self, screening_type: str, days_ahead: int = 14) -> List[Dict[str, Any]]:
        """Get available appointment time slots for booking"""
        # Simulate available time slots
        slots = []
        base_date = datetime.now().date()
        
        for day_offset in range(1, days_ahead + 1):
            appointment_date = base_date + timedelta(days=day_offset)
            
            # Skip weekends for demo
            if appointment_date.weekday() < 5:  # Monday = 0, Friday = 4
                # Morning slots
                for hour in [9, 10, 11]:
                    slots.append({
                        "date": appointment_date.isoformat(),
                        "time": f"{hour:02d}:00",
                        "datetime": f"{appointment_date.isoformat()} {hour:02d}:00:00",
                        "available": True,
                        "screening_type": screening_type
                    })
                
                # Afternoon slots  
                for hour in [14, 15, 16]:
                    slots.append({
                        "date": appointment_date.isoformat(),
                        "time": f"{hour:02d}:00",
                        "datetime": f"{appointment_date.isoformat()} {hour:02d}:00:00",
                        "available": True,
                        "screening_type": screening_type
                    })
        
        return slots[:20]  # Return first 20 available slots