#!/usr/bin/env python3
"""
Sample Patient Data Generation Script
Generates realistic healthcare data for testing the care gap automation system.
"""

import os
import sys
import random
from datetime import datetime, timedelta, date
from typing import List, Dict, Any

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from faker import Faker
from app.config.database import SessionLocal, create_tables
from app.models import Patient, CareGap, Appointment, Workflow, Campaign
from app.models.care_gap import PriorityLevel, CareGapStatus
from app.models.appointment import AppointmentStatus
from app.models.workflow import WorkflowStatus
from app.models.campaign import CampaignStatus

fake = Faker()

# Healthcare-specific data
SCREENING_TYPES = [
    "Annual Physical",
    "Mammography",
    "Colonoscopy", 
    "Blood Work",
    "Cholesterol Screening",
    "Diabetes Screening",
    "Bone Density Test",
    "Eye Exam",
    "Skin Cancer Screening",
    "Prostate Exam",
    "Pap Smear",
    "Cardiac Stress Test"
]

INSURANCE_PROVIDERS = [
    {"name": "Blue Cross Blue Shield", "group": "BCBS001", "member_id_prefix": "BCBS"},
    {"name": "Aetna", "group": "AET001", "member_id_prefix": "AET"},
    {"name": "UnitedHealthcare", "group": "UHC001", "member_id_prefix": "UHC"},
    {"name": "Cigna", "group": "CIG001", "member_id_prefix": "CIG"},
    {"name": "Humana", "group": "HUM001", "member_id_prefix": "HUM"},
    {"name": "Kaiser Permanente", "group": "KP001", "member_id_prefix": "KP"},
    {"name": "Anthem", "group": "ANT001", "member_id_prefix": "ANT"},
    {"name": "Medicare", "group": "MED001", "member_id_prefix": "MED"}
]

RISK_FACTORS = [
    "Hypertension",
    "Diabetes Type 2", 
    "High Cholesterol",
    "Family History of Heart Disease",
    "Family History of Cancer",
    "Smoking History",
    "Obesity (BMI > 30)",
    "Sedentary Lifestyle",
    "Alcohol Use",
    "Family History of Diabetes"
]

CONTACT_METHODS = ["email", "phone", "text", "mail"]

DOCTORS = [
    "Dr. Sarah Johnson",
    "Dr. Michael Chen", 
    "Dr. Emily Rodriguez",
    "Dr. James Wilson",
    "Dr. Lisa Thompson",
    "Dr. David Kim",
    "Dr. Maria Garcia",
    "Dr. Robert Miller",
    "Dr. Jennifer Davis",
    "Dr. Christopher Lee"
]

LOCATIONS = [
    "Main Medical Center - Building A",
    "Downtown Clinic", 
    "Westside Health Center",
    "Eastside Family Practice",
    "Northgate Medical Plaza",
    "Southpoint Health Clinic",
    "University Hospital",
    "Community Health Center",
    "Specialty Care Center",
    "Women's Health Clinic"
]

def generate_insurance_info() -> Dict[str, Any]:
    """Generate realistic insurance information"""
    provider = random.choice(INSURANCE_PROVIDERS)
    return {
        "provider": provider["name"],
        "group_number": provider["group"],
        "member_id": f"{provider['member_id_prefix']}{fake.random_number(digits=8)}",
        "policy_holder": fake.name(),
        "effective_date": fake.date_between(start_date='-2y', end_date='today').isoformat(),
        "copay": random.choice([10, 15, 20, 25, 30, 35])
    }

def generate_risk_factors() -> str:
    """Generate realistic risk factors"""
    num_factors = random.randint(0, 4)
    if num_factors == 0:
        return "None reported"
    
    selected_factors = random.sample(RISK_FACTORS, num_factors)
    return ", ".join(selected_factors)

def calculate_age_from_dob(date_of_birth: date) -> int:
    """Calculate age from date of birth"""
    today = date.today()
    return today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))

def generate_patients(session, num_patients: int = 25) -> List[Patient]:
    """Generate sample patients"""
    patients = []
    
    for i in range(num_patients):
        # Generate date of birth (ages 18-85)
        dob = fake.date_of_birth(minimum_age=18, maximum_age=85)
        age = calculate_age_from_dob(dob)
        
        patient = Patient(
            name=fake.name(),
            age=age,
            email=fake.unique.email(),
            phone=fake.phone_number()[:20],  # Truncate to fit field limit
            date_of_birth=dob,
            insurance_info=generate_insurance_info(),
            risk_factors=generate_risk_factors(),
            preferred_contact_method=random.choice(CONTACT_METHODS)
        )
        
        session.add(patient)
        patients.append(patient)
    
    session.commit()
    print(f"Generated {num_patients} patients")
    return patients

def generate_care_gaps(session, patients: List[Patient]) -> List[CareGap]:
    """Generate care gaps for patients"""
    care_gaps = []
    
    for patient in patients:
        # Each patient has 1-3 care gaps
        num_gaps = random.randint(1, 3)
        patient_screening_types = random.sample(SCREENING_TYPES, num_gaps)
        
        for screening_type in patient_screening_types:
            # Generate overdue scenarios
            if screening_type == "Annual Physical":
                max_overdue = 450  # 15 months
            elif screening_type in ["Mammography", "Colonoscopy"]:
                max_overdue = 730  # 2 years
            elif screening_type == "Blood Work":
                max_overdue = 180  # 6 months
            else:
                max_overdue = 365  # 1 year
            
            overdue_days = random.randint(1, max_overdue)
            last_screening = fake.date_between(
                start_date=f'-{overdue_days + 365}d',
                end_date=f'-{overdue_days}d'
            )
            
            # Assign priority based on overdue days and screening type
            if screening_type in ["Colonoscopy", "Mammography"] and overdue_days > 365:
                priority = PriorityLevel.HIGH
            elif overdue_days > 180:
                priority = PriorityLevel.MEDIUM
            elif overdue_days > 90:
                priority = PriorityLevel.MEDIUM
            else:
                priority = PriorityLevel.LOW
            
            # Some gaps are urgent due to risk factors
            if "Diabetes" in patient.risk_factors and screening_type == "Blood Work":
                priority = PriorityLevel.URGENT
            elif "Family History of Cancer" in patient.risk_factors and screening_type in ["Mammography", "Colonoscopy"]:
                priority = PriorityLevel.HIGH
            
            care_gap = CareGap(
                patient_id=patient.id,
                screening_type=screening_type,
                last_screening_date=last_screening,
                overdue_days=overdue_days,
                priority_level=priority,
                status=random.choice([CareGapStatus.OPEN, CareGapStatus.IN_PROGRESS, CareGapStatus.OPEN, CareGapStatus.OPEN])  # Most are open
            )
            
            session.add(care_gap)
            care_gaps.append(care_gap)
    
    session.commit()
    print(f"Generated {len(care_gaps)} care gaps")
    return care_gaps

def generate_appointments(session, care_gaps: List[CareGap]) -> List[Appointment]:
    """Generate appointments for some care gaps"""
    appointments = []
    
    # Generate appointments for about 40% of care gaps
    care_gaps_with_appointments = random.sample(care_gaps, int(len(care_gaps) * 0.4))
    
    for care_gap in care_gaps_with_appointments:
        # Schedule appointment 1-30 days in the future
        appointment_date = fake.date_time_between(
            start_date='+1d',
            end_date='+30d'
        )
        
        appointment = Appointment(
            patient_id=care_gap.patient_id,
            care_gap_id=care_gap.id,
            appointment_date=appointment_date,
            doctor_name=random.choice(DOCTORS),
            location=random.choice(LOCATIONS),
            status=random.choice([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.SCHEDULED,  # Weight towards scheduled
                AppointmentStatus.SCHEDULED
            ]),
            confirmation_code=f"HC{fake.random_number(digits=6)}"
        )
        
        session.add(appointment)
        appointments.append(appointment)
    
    session.commit()
    print(f"Generated {len(appointments)} appointments")
    return appointments

def generate_workflows(session) -> List[Workflow]:
    """Generate sample workflows"""
    workflows = []
    
    workflow_names = [
        "Mammography Outreach Campaign Q4 2024",
        "Annual Physical Reminder Campaign",
        "High-Risk Patient Follow-up",
        "Diabetes Screening Initiative",
        "Colonoscopy Overdue Patients"
    ]
    
    for name in workflow_names:
        workflow = Workflow(
            campaign_name=name,
            status=random.choice([
                WorkflowStatus.COMPLETED,
                WorkflowStatus.RUNNING,
                WorkflowStatus.PENDING
            ]),
            started_at=fake.date_time_between(start_date='-30d', end_date='now') if random.choice([True, False]) else None,
            completed_at=fake.date_time_between(start_date='-15d', end_date='now') if random.choice([True, False]) else None,
            total_patients=random.randint(15, 50),
            agents_involved="Care Coordinator Agent, Appointment Scheduler Agent, Follow-up Agent"
        )
        
        session.add(workflow)
        workflows.append(workflow)
    
    session.commit()
    print(f"Generated {len(workflows)} workflows")
    return workflows

def generate_campaigns(session, workflows: List[Workflow]) -> List[Campaign]:
    """Generate sample campaigns"""
    campaigns = []
    
    for workflow in workflows:
        campaign = Campaign(
            workflow_id=workflow.id,
            name=workflow.campaign_name,
            filters={
                "age_range": {"min": random.randint(18, 40), "max": random.randint(50, 85)},
                "screening_types": random.sample(SCREENING_TYPES, random.randint(1, 3)),
                "priority_levels": ["high", "urgent"] if "High-Risk" in workflow.campaign_name else ["medium", "high"],
                "overdue_days_min": random.randint(30, 180)
            },
            status=random.choice([
                CampaignStatus.ACTIVE,
                CampaignStatus.COMPLETED,
                CampaignStatus.DRAFT
            ]),
            results_summary=f"Contacted {random.randint(20, 45)} patients, {random.randint(8, 20)} appointments scheduled, {random.randint(3, 8)} completed screenings" if random.choice([True, False]) else None
        )
        
        session.add(campaign)
        campaigns.append(campaign)
    
    session.commit()
    print(f"Generated {len(campaigns)} campaigns")
    return campaigns

def main():
    """Main function to generate all sample data"""
    print("🏥 Healthcare Care Gap Automation - Sample Data Generator")
    print("=" * 60)
    
    # Create database tables
    print("Creating database tables...")
    create_tables()
    
    # Create database session
    session = SessionLocal()
    
    try:
        # Generate data
        print("\n📋 Generating sample data...")
        
        patients = generate_patients(session, 30)  # Generate 30 patients
        care_gaps = generate_care_gaps(session, patients)
        appointments = generate_appointments(session, care_gaps)
        workflows = generate_workflows(session)
        campaigns = generate_campaigns(session, workflows)
        
        print(f"\n✅ Sample data generation completed successfully!")
        print(f"   • {len(patients)} patients created")
        print(f"   • {len(care_gaps)} care gaps identified")
        print(f"   • {len(appointments)} appointments scheduled")
        print(f"   • {len(workflows)} workflows created")
        print(f"   • {len(campaigns)} campaigns configured")
        
        print(f"\n📊 Summary Statistics:")
        
        # Priority distribution
        urgent_count = session.query(CareGap).filter(CareGap.priority_level == PriorityLevel.URGENT).count()
        high_count = session.query(CareGap).filter(CareGap.priority_level == PriorityLevel.HIGH).count()
        medium_count = session.query(CareGap).filter(CareGap.priority_level == PriorityLevel.MEDIUM).count()
        low_count = session.query(CareGap).filter(CareGap.priority_level == PriorityLevel.LOW).count()
        
        print(f"   • Urgent care gaps: {urgent_count}")
        print(f"   • High priority: {high_count}")
        print(f"   • Medium priority: {medium_count}")
        print(f"   • Low priority: {low_count}")
        
        # Most overdue screening type
        from sqlalchemy import func
        most_common_screening = session.query(CareGap.screening_type, func.count(CareGap.screening_type)).group_by(CareGap.screening_type).order_by(func.count(CareGap.screening_type).desc()).first()
        if most_common_screening:
            print(f"   • Most common overdue screening: {most_common_screening[0]}")
        
    except Exception as e:
        print(f"❌ Error generating sample data: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()