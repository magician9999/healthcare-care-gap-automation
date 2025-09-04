#!/usr/bin/env python3
"""
Sample data population script for Healthcare Care Gap Automation
Inserts 60 patients with realistic healthcare screening data including care gaps
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, timedelta
from faker import Faker
import random
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Import models and database config
from app.models.patient import Patient
from app.models.care_gap import CareGap, PriorityLevel, CareGapStatus
from app.models.appointment import Appointment, AppointmentStatus
from app.config.database import DATABASE_URL

# Initialize Faker
fake = Faker()

# Common screening tests with typical intervals (in days)
SCREENING_TESTS = {
    "mammography": {"interval": 365, "age_range": (40, 75)},
    "colonoscopy": {"interval": 3650, "age_range": (50, 75)},  # 10 years
    "pap_smear": {"interval": 1095, "age_range": (21, 65)},   # 3 years
    "blood_pressure_check": {"interval": 365, "age_range": (18, 85)},
    "cholesterol_screening": {"interval": 1825, "age_range": (20, 75)},  # 5 years
    "diabetes_screening": {"interval": 1095, "age_range": (35, 75)},     # 3 years
    "bone_density_scan": {"interval": 730, "age_range": (50, 85)},       # 2 years
    "eye_exam": {"interval": 730, "age_range": (18, 85)},                # 2 years
    "skin_cancer_screening": {"interval": 365, "age_range": (18, 85)},
    "prostate_screening": {"interval": 365, "age_range": (50, 75)},      # Men only
    "breast_self_exam": {"interval": 30, "age_range": (20, 75)},         # Women only
    "cervical_cancer_screening": {"interval": 1095, "age_range": (21, 65)}, # 3 years
    "lung_cancer_screening": {"interval": 365, "age_range": (55, 80)},   # High risk
    "hepatitis_b_screening": {"interval": 1825, "age_range": (18, 65)},  # 5 years
    "osteoporosis_screening": {"interval": 730, "age_range": (65, 85)}   # 2 years
}

# Risk factors
RISK_FACTORS = [
    "smoking", "diabetes", "hypertension", "high_cholesterol", "obesity", 
    "family_history_cancer", "family_history_heart_disease", "sedentary_lifestyle",
    "alcohol_use", "history_of_stroke", "chronic_kidney_disease", "asthma"
]

def create_sample_patients():
    """Create 60 sample patients with Shivanshu Saxena as the first patient"""
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("Creating 60 sample patients with care gap data...")
        
        patients = []
        
        # First patient - Shivanshu Saxena
        shivanshu_dob = date(1990, 5, 15)  # 33 years old
        shivanshu_age = (date.today() - shivanshu_dob).days // 365
        
        shivanshu = Patient(
            name="Shivanshu Saxena",
            age=shivanshu_age,
            email="shivanshusaxenaofficial@gmail.com",
            phone="+91-9876543210",
            date_of_birth=shivanshu_dob,
            insurance_info={
                "provider": "Star Health Insurance",
                "policy_number": "SH2024001",
                "coverage_type": "comprehensive"
            },
            risk_factors="hypertension, family_history_diabetes",
            preferred_contact_method="email"
        )
        patients.append(shivanshu)
        
        # Generate 59 additional patients
        for i in range(59):
            # Generate random age between 18-85
            age = random.randint(18, 85)
            birth_year = datetime.now().year - age
            birth_month = random.randint(1, 12)
            birth_day = random.randint(1, 28)
            dob = date(birth_year, birth_month, birth_day)
            
            # Generate patient data
            first_name = fake.first_name()
            last_name = fake.last_name()
            name = f"{first_name} {last_name}"
            email = f"{first_name.lower()}.{last_name.lower()}@{fake.free_email_domain()}"
            
            # Select random risk factors
            num_risks = random.randint(0, 4)
            selected_risks = random.sample(RISK_FACTORS, num_risks) if num_risks > 0 else []
            
            patient = Patient(
                name=name,
                age=age,
                email=email,
                phone=fake.phone_number()[:20],
                date_of_birth=dob,
                insurance_info={
                    "provider": random.choice(["Blue Cross", "Aetna", "Cigna", "UnitedHealth", "Kaiser"]),
                    "policy_number": fake.bothify("??#######"),
                    "coverage_type": random.choice(["basic", "standard", "comprehensive"])
                },
                risk_factors=", ".join(selected_risks),
                preferred_contact_method=random.choice(["email", "phone", "text"])
            )
            patients.append(patient)
        
        # Add all patients to database
        db.add_all(patients)
        db.commit()
        
        # Refresh to get patient IDs
        for patient in patients:
            db.refresh(patient)
        
        print(f"Created {len(patients)} patients successfully")
        
        # Now create care gaps for each patient
        care_gaps = []
        appointments = []
        
        for patient in patients:
            # Determine which screening tests apply based on age and gender
            applicable_tests = []
            
            for test_name, test_info in SCREENING_TESTS.items():
                age_min, age_max = test_info["age_range"]
                
                # Skip gender-specific tests based on name patterns (simplified approach)
                if test_name in ["prostate_screening"] and "female" in patient.name.lower():
                    continue
                if test_name in ["mammography", "pap_smear", "breast_self_exam", "cervical_cancer_screening"]:
                    # Assume 50% are female for simplicity
                    if random.choice([True, False]):
                        continue
                
                if age_min <= patient.age <= age_max:
                    applicable_tests.append((test_name, test_info))
            
            # Create care gaps for this patient (randomly select 2-5 tests per patient)
            num_tests = min(random.randint(2, 5), len(applicable_tests))
            selected_tests = random.sample(applicable_tests, num_tests) if applicable_tests else []
            
            for test_name, test_info in selected_tests:
                # Calculate last screening date (some overdue, some current)
                interval_days = test_info["interval"]
                
                # 60% chance of being overdue, 40% chance of being current
                if random.random() < 0.6:
                    # Overdue - last screening was beyond the interval
                    days_overdue = random.randint(1, min(interval_days, 730))  # Max 2 years overdue
                    last_screening = date.today() - timedelta(days=interval_days + days_overdue)
                    overdue_days = days_overdue
                    
                    # Determine priority based on how overdue
                    if days_overdue > 365:
                        priority = PriorityLevel.URGENT
                    elif days_overdue > 180:
                        priority = PriorityLevel.HIGH
                    elif days_overdue > 90:
                        priority = PriorityLevel.MEDIUM
                    else:
                        priority = PriorityLevel.LOW
                        
                    status = CareGapStatus.OPEN
                else:
                    # Current - last screening was within the interval
                    days_since_last = random.randint(1, interval_days - 30)
                    last_screening = date.today() - timedelta(days=days_since_last)
                    overdue_days = 0
                    priority = PriorityLevel.LOW
                    status = CareGapStatus.CLOSED
                
                care_gap = CareGap(
                    patient_id=patient.id,
                    screening_type=test_name,
                    last_screening_date=last_screening,
                    overdue_days=overdue_days,
                    priority_level=priority,
                    status=status
                )
                care_gaps.append(care_gap)
                
                # Create appointments for some open care gaps (30% chance)
                if status == CareGapStatus.OPEN and random.random() < 0.3:
                    appointment_date = datetime.now() + timedelta(days=random.randint(1, 30))
                    
                    appointment = Appointment(
                        patient_id=patient.id,
                        care_gap_id=None,  # Will be set after care_gap is saved
                        appointment_date=appointment_date,
                        doctor_name=fake.name_male() if random.choice([True, False]) else fake.name_female(),
                        location=f"{fake.street_address()}, {fake.city()}",
                        status=random.choice([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
                        confirmation_code=fake.bothify("???###")
                    )
                    appointments.append((appointment, care_gap))
        
        # Add care gaps to database
        db.add_all(care_gaps)
        db.commit()
        
        # Refresh care gaps to get IDs and update appointments
        for care_gap in care_gaps:
            db.refresh(care_gap)
        
        # Update appointment care_gap_ids
        final_appointments = []
        for appointment, care_gap in appointments:
            appointment.care_gap_id = care_gap.id
            final_appointments.append(appointment)
        
        # Add appointments to database
        if final_appointments:
            db.add_all(final_appointments)
            db.commit()
        
        print(f"Created {len(care_gaps)} care gaps")
        print(f"Created {len(final_appointments)} appointments")
        
        # Print summary statistics
        open_gaps = len([cg for cg in care_gaps if cg.status == CareGapStatus.OPEN])
        urgent_gaps = len([cg for cg in care_gaps if cg.priority_level == PriorityLevel.URGENT])
        high_priority_gaps = len([cg for cg in care_gaps if cg.priority_level == PriorityLevel.HIGH])
        
        print(f"\nSummary:")
        print(f"   Total Patients: {len(patients)}")
        print(f"   Open Care Gaps: {open_gaps}")
        print(f"   Urgent Priority: {urgent_gaps}")
        print(f"   High Priority: {high_priority_gaps}")
        print(f"   Scheduled Appointments: {len(final_appointments)}")
        
        print(f"\nSample data population completed successfully!")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_patients()