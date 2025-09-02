#!/usr/bin/env python3

import sys
import os
from pathlib import Path

# Add the backend app directory to the Python path for model imports
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.append(str(backend_path))

import random
import logging
from datetime import datetime, date, timedelta
from faker import Faker
from typing import List, Dict, Any

from database import (
    get_db_session,
    create_tables,
    test_database_connection,
    Patient,
    CareGap,
    CareGapStatus,
    PriorityLevel,
    Appointment,
    AppointmentStatus
)
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Faker
fake = Faker()
Faker.seed(42)  # For reproducible data
random.seed(42)


class SampleDataGenerator:
    """Generate sample healthcare data for testing"""
    
    def __init__(self):
        self.screening_types = [
            "mammogram",
            "colonoscopy", 
            "blood_pressure_check",
            "cholesterol_screening",
            "diabetes_screening",
            "bone_density_scan",
            "pap_smear",
            "prostate_exam",
            "eye_exam",
            "hearing_test"
        ]
        
        self.contact_methods = ["email", "phone", "sms", "mail"]
        
        self.risk_factors_templates = [
            "Family history of heart disease",
            "Smoker, 10+ years",
            "Obesity (BMI > 30)",
            "Diabetes Type 2",
            "High blood pressure",
            "High cholesterol",
            "Sedentary lifestyle",
            "Family history of cancer",
            "Alcohol consumption",
            "Age-related risks"
        ]
        
        self.doctors = [
            "Dr. Sarah Johnson",
            "Dr. Michael Chen", 
            "Dr. Emily Rodriguez",
            "Dr. David Kim",
            "Dr. Lisa Thompson",
            "Dr. Robert Wilson",
            "Dr. Maria Garcia",
            "Dr. James Park"
        ]
        
        self.locations = [
            "Main Medical Center - Room 101",
            "Downtown Clinic - Suite 205",
            "Community Health Center",
            "Specialty Care Building - Floor 3",
            "Outpatient Services Wing",
            "Women's Health Center",
            "Cardiology Department",
            "Preventive Care Clinic"
        ]
    
    def generate_patient_data(self, count: int = 30) -> List[Dict[str, Any]]:
        """Generate sample patient data"""
        patients = []
        
        for i in range(count):
            # Generate basic patient info
            first_name = fake.first_name()
            last_name = fake.last_name()
            birth_date = fake.date_of_birth(minimum_age=18, maximum_age=85)
            age = (date.today() - birth_date).days // 365
            
            # Generate insurance info
            insurance_info = {
                "provider": fake.random_element([
                    "Blue Cross Blue Shield", "Aetna", "Cigna", 
                    "UnitedHealth", "Kaiser Permanente", "Medicare", "Medicaid"
                ]),
                "policy_number": fake.bothify("POL-####-????"),
                "group_number": fake.bothify("GRP-####"),
                "coverage_type": fake.random_element(["Full Coverage", "Basic", "Premium"])
            }
            
            # Generate risk factors
            num_risk_factors = random.randint(1, 4)
            risk_factors = "; ".join(random.sample(self.risk_factors_templates, num_risk_factors))
            
            patient_data = {
                "name": f"{first_name} {last_name}",
                "age": age,
                "email": fake.email(),
                "phone": fake.phone_number()[:20],  # Limit to 20 chars
                "date_of_birth": birth_date,
                "insurance_info": insurance_info,
                "risk_factors": risk_factors,
                "preferred_contact_method": random.choice(self.contact_methods)
            }
            
            patients.append(patient_data)
        
        return patients
    
    def generate_care_gaps_for_patient(self, patient_id: int, patient_age: int) -> List[Dict[str, Any]]:
        """Generate care gaps for a specific patient based on age"""
        care_gaps = []
        
        # Age-appropriate screenings
        age_appropriate_screenings = []
        
        if patient_age >= 40:
            age_appropriate_screenings.extend(["mammogram", "colonoscopy"])
        if patient_age >= 50:
            age_appropriate_screenings.extend(["prostate_exam", "bone_density_scan"])
        if patient_age >= 18:
            age_appropriate_screenings.extend([
                "blood_pressure_check", "cholesterol_screening", 
                "diabetes_screening", "eye_exam"
            ])
        if patient_age >= 21:
            age_appropriate_screenings.append("pap_smear")
        
        # Generate 2-5 care gaps per patient
        num_gaps = random.randint(2, 5)
        selected_screenings = random.sample(
            age_appropriate_screenings or self.screening_types[:5], 
            min(num_gaps, len(age_appropriate_screenings) or 5)
        )
        
        for screening in selected_screenings:
            # 70% chance of being overdue
            is_overdue = random.random() < 0.7
            
            if is_overdue:
                # Overdue by 30-365 days
                overdue_days = random.randint(30, 365)
                last_screening_date = date.today() - timedelta(days=365 + overdue_days)
                status = CareGapStatus.OPEN
            else:
                # Up to date or recently completed
                overdue_days = 0
                last_screening_date = date.today() - timedelta(days=random.randint(1, 180))
                status = random.choice([CareGapStatus.OPEN, CareGapStatus.CLOSED])
            
            # Assign priority based on overdue days
            if overdue_days > 180:
                priority = PriorityLevel.URGENT
            elif overdue_days > 90:
                priority = PriorityLevel.HIGH
            elif overdue_days > 30:
                priority = PriorityLevel.MEDIUM
            else:
                priority = PriorityLevel.LOW
            
            care_gap = {
                "patient_id": patient_id,
                "screening_type": screening,
                "last_screening_date": last_screening_date,
                "overdue_days": overdue_days,
                "priority_level": priority,
                "status": status
            }
            
            care_gaps.append(care_gap)
        
        return care_gaps
    
    def generate_appointments_for_patient(self, patient_id: int, care_gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate appointments for a patient's care gaps"""
        appointments = []
        
        # Generate appointments for some care gaps (40% chance)
        for care_gap in care_gaps:
            if random.random() < 0.4:  # 40% chance of having an appointment
                # Future appointment (1-90 days from now)
                appointment_date = datetime.now() + timedelta(days=random.randint(1, 90))
                
                appointment = {
                    "patient_id": patient_id,
                    "care_gap_id": None,  # Will be set after care gap is created
                    "appointment_date": appointment_date,
                    "doctor_name": random.choice(self.doctors),
                    "location": random.choice(self.locations),
                    "status": random.choice([
                        AppointmentStatus.SCHEDULED,
                        AppointmentStatus.CONFIRMED
                    ]),
                    "confirmation_code": fake.bothify("CONF-????-####")
                }
                
                appointments.append((appointment, care_gap["screening_type"]))
        
        return appointments
    
    async def create_sample_data(self, num_patients: int = 30):
        """Create sample data in the database"""
        logger.info(f"Generating sample data for {num_patients} patients...")
        
        try:
            with get_db_session() as session:
                # Clear existing data (optional)
                logger.info("Checking for existing data...")
                existing_patients = session.query(Patient).count()
                if existing_patients > 0:
                    logger.warning(f"Found {existing_patients} existing patients. Proceeding with additional data.")
                
                # Generate patients
                patients_data = self.generate_patient_data(num_patients)
                created_patients = []
                
                logger.info("Creating patients...")
                for patient_data in patients_data:
                    patient = Patient(**patient_data)
                    session.add(patient)
                    session.flush()  # Get the ID
                    created_patients.append(patient)
                
                logger.info(f"Created {len(created_patients)} patients")
                
                # Generate care gaps
                logger.info("Creating care gaps...")
                all_care_gaps = []
                for patient in created_patients:
                    care_gaps_data = self.generate_care_gaps_for_patient(patient.id, patient.age)
                    for gap_data in care_gaps_data:
                        care_gap = CareGap(**gap_data)
                        session.add(care_gap)
                        session.flush()  # Get the ID
                        all_care_gaps.append((care_gap, patient.id))
                
                logger.info(f"Created {len(all_care_gaps)} care gaps")
                
                # Generate appointments
                logger.info("Creating appointments...")
                appointment_count = 0
                
                # Group care gaps by patient
                patient_care_gaps = {}
                for care_gap, patient_id in all_care_gaps:
                    if patient_id not in patient_care_gaps:
                        patient_care_gaps[patient_id] = []
                    patient_care_gaps[patient_id].append(care_gap)
                
                for patient_id, care_gaps in patient_care_gaps.items():
                    # Convert care gaps to dict format for appointment generation
                    care_gaps_dict = [
                        {
                            "screening_type": gap.screening_type,
                            "care_gap_id": gap.id
                        } 
                        for gap in care_gaps
                    ]
                    
                    appointments_data = self.generate_appointments_for_patient(patient_id, care_gaps_dict)
                    
                    for appointment_data, screening_type in appointments_data:
                        # Find matching care gap
                        matching_care_gap = next(
                            (gap for gap in care_gaps if gap.screening_type == screening_type),
                            None
                        )
                        
                        if matching_care_gap:
                            appointment_data["care_gap_id"] = matching_care_gap.id
                            appointment = Appointment(**appointment_data)
                            session.add(appointment)
                            appointment_count += 1
                
                logger.info(f"Created {appointment_count} appointments")
                
                # Commit all changes
                session.commit()
                logger.info("All sample data committed successfully!")
                
                # Print summary
                total_patients = session.query(Patient).count()
                total_care_gaps = session.query(CareGap).count()
                total_appointments = session.query(Appointment).count()
                overdue_gaps = session.query(CareGap).filter(
                    CareGap.status == CareGapStatus.OPEN,
                    CareGap.overdue_days > 0
                ).count()
                
                print("\n" + "="*60)
                print("SAMPLE DATA GENERATION COMPLETE")
                print("="*60)
                print(f"Total Patients: {total_patients}")
                print(f"Total Care Gaps: {total_care_gaps}")
                print(f"Overdue Care Gaps: {overdue_gaps}")
                print(f"Total Appointments: {total_appointments}")
                print("="*60)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to create sample data: {e}")
            return False
    
    async def clear_all_data(self):
        """Clear all data from the database (use with caution!)"""
        logger.warning("Clearing all data from database...")
        
        try:
            with get_db_session() as session:
                # Delete in order due to foreign key constraints
                session.query(Appointment).delete()
                session.query(CareGap).delete()
                session.query(Patient).delete()
                session.commit()
                
                logger.info("All data cleared successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear data: {e}")
            return False


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate sample healthcare data")
    parser.add_argument("--patients", type=int, default=30, help="Number of patients to generate")
    parser.add_argument("--clear", action="store_true", help="Clear all existing data first")
    parser.add_argument("--test-connection", action="store_true", help="Test database connection only")
    
    args = parser.parse_args()
    
    # Test database connection
    if not test_database_connection():
        logger.error("Database connection failed. Please check your configuration.")
        return False
    
    if args.test_connection:
        logger.info("Database connection successful!")
        return True
    
    # Create tables if they don't exist
    create_tables()
    
    generator = SampleDataGenerator()
    
    # Clear data if requested
    if args.clear:
        success = await generator.clear_all_data()
        if not success:
            return False
    
    # Generate sample data
    success = await generator.create_sample_data(args.patients)
    return success


if __name__ == "__main__":
    import asyncio
    import sys
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)