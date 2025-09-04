#!/usr/bin/env python3
"""
Add care gaps to existing patients in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, timedelta
import random
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Import models and database config
from app.models.patient import Patient
from app.models.care_gap import CareGap, PriorityLevel, CareGapStatus
from app.models.appointment import Appointment, AppointmentStatus
from app.config.database import DATABASE_URL

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

def add_care_gaps():
    """Add care gaps for all existing patients"""
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get all patients
        patients = db.query(Patient).all()
        print(f"Adding care gaps for {len(patients)} patients...")
        
        care_gaps = []
        appointments = []
        
        for patient in patients:
            print(f"Processing patient: {patient.name}")
            
            # Determine which screening tests apply based on age
            applicable_tests = []
            
            for test_name, test_info in SCREENING_TESTS.items():
                age_min, age_max = test_info["age_range"]
                
                # Skip gender-specific tests based on common name patterns
                if test_name in ["prostate_screening"]:
                    # Skip for likely female names (simplified approach)
                    if any(name in patient.name.lower() for name in ["sarah", "mary", "jessica", "jennifer", "lisa", "michelle", "kimberly", "amy", "angela", "elizabeth", "patricia", "susan", "donna", "carol", "ruth", "sandra", "deborah", "christine", "samantha", "debbie", "nancy", "heather", "diane", "julie", "joyce", "victoria", "kelly", "christina"]):
                        continue
                
                if test_name in ["mammography", "pap_smear", "breast_self_exam", "cervical_cancer_screening"]:
                    # Skip for likely male names (simplified approach)  
                    if any(name in patient.name.lower() for name in ["john", "michael", "william", "james", "robert", "david", "richard", "thomas", "charles", "christopher", "daniel", "matthew", "anthony", "mark", "donald", "steven", "paul", "andrew", "joshua", "kenneth", "kevin", "brian", "george", "timothy", "ronald", "jason", "edward", "jeffrey", "ryan", "jacob", "gary", "nicholas", "eric", "jonathan", "stephen", "larry", "bradley", "alec", "david", "cody", "matthew"]):
                        continue
                
                if age_min <= patient.age <= age_max:
                    applicable_tests.append((test_name, test_info))
            
            # Create care gaps for this patient (randomly select 2-5 tests per patient)
            num_tests = min(random.randint(2, 5), len(applicable_tests))
            selected_tests = random.sample(applicable_tests, num_tests) if applicable_tests else []
            
            for test_name, test_info in selected_tests:
                # Calculate last screening date (some overdue, some current)
                interval_days = test_info["interval"]
                
                # 70% chance of being overdue, 30% chance of being current
                if random.random() < 0.7:
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
                    days_since_last = random.randint(1, max(30, interval_days // 2))
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
        
        # Add care gaps to database in batches
        batch_size = 50
        for i in range(0, len(care_gaps), batch_size):
            batch = care_gaps[i:i+batch_size]
            db.add_all(batch)
            db.commit()
            print(f"Added batch {i//batch_size + 1} ({len(batch)} care gaps)")
        
        # Print summary statistics
        total_gaps = len(care_gaps)
        open_gaps = len([cg for cg in care_gaps if cg.status == CareGapStatus.OPEN])
        urgent_gaps = len([cg for cg in care_gaps if cg.priority_level == PriorityLevel.URGENT])
        high_priority_gaps = len([cg for cg in care_gaps if cg.priority_level == PriorityLevel.HIGH])
        
        print(f"\nSummary:")
        print(f"   Total Care Gaps Created: {total_gaps}")
        print(f"   Open Care Gaps: {open_gaps}")
        print(f"   Urgent Priority: {urgent_gaps}")
        print(f"   High Priority: {high_priority_gaps}")
        
        print(f"\nCare gaps added successfully!")
        
    except Exception as e:
        print(f"Error adding care gaps: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_care_gaps()