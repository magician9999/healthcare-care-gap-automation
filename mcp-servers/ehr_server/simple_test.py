#!/usr/bin/env python3

"""
Simple test for EHR MCP Server core functionality
Tests the database operations without the full MCP protocol
"""

import asyncio
import json
import logging
from database import (
    get_db_session, 
    Patient, 
    CareGap, 
    CareGapStatus, 
    PriorityLevel,
    Appointment,
    AppointmentStatus
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_overdue_patients():
    """Test overdue patients functionality"""
    print("\n=== Testing Overdue Patients ===")
    
    try:
        with get_db_session() as session:
            # Get overdue care gaps
            overdue_gaps = session.query(CareGap).filter(
                CareGap.status == CareGapStatus.OPEN,
                CareGap.overdue_days > 0
            ).limit(10).all()
            
            # Group by patient
            patient_gaps = {}
            for gap in overdue_gaps:
                if gap.patient_id not in patient_gaps:
                    patient_gaps[gap.patient_id] = []
                patient_gaps[gap.patient_id].append(gap)
            
            # Get patient details
            results = []
            for patient_id, gaps in patient_gaps.items():
                patient = session.query(Patient).filter(Patient.id == patient_id).first()
                if patient:
                    overdue_gaps_info = []
                    for gap in gaps:
                        overdue_gaps_info.append({
                            "care_gap_id": gap.id,
                            "screening_type": gap.screening_type,
                            "overdue_days": gap.overdue_days,
                            "priority_level": gap.priority_level.value,
                            "last_screening_date": gap.last_screening_date.isoformat() if gap.last_screening_date else None
                        })
                    
                    results.append({
                        "patient_id": patient.id,
                        "name": patient.name,
                        "age": patient.age,
                        "email": patient.email,
                        "overdue_care_gaps": overdue_gaps_info,
                        "total_overdue_gaps": len(overdue_gaps_info)
                    })
            
            print(f"✓ Found {len(results)} patients with overdue care gaps")
            
            # Show first few results
            for result in results[:3]:
                print(f"  - {result['name']} (age {result['age']}): {result['total_overdue_gaps']} overdue gap(s)")
                for gap in result['overdue_care_gaps'][:2]:  # Show max 2 gaps per patient
                    print(f"    * {gap['screening_type']}: {gap['overdue_days']} days overdue")
            
            return True
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_patient_details():
    """Test patient details functionality"""
    print("\n=== Testing Patient Details ===")
    
    try:
        with get_db_session() as session:
            # Get first patient
            patient = session.query(Patient).first()
            if not patient:
                print("✗ No patients found")
                return False
            
            # Get patient's care gaps
            care_gaps = session.query(CareGap).filter(
                CareGap.patient_id == patient.id
            ).all()
            
            # Get patient's appointments
            appointments = session.query(Appointment).filter(
                Appointment.patient_id == patient.id
            ).all()
            
            # Build response
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
                "total_care_gaps": len(care_gaps),
                "open_care_gaps": len([g for g in care_gaps if g.status == CareGapStatus.OPEN]),
                "total_appointments": len(appointments)
            }
            
            print(f"✓ Patient details for {patient_details['name']}:")
            print(f"  - Age: {patient_details['age']}")
            print(f"  - Care gaps: {patient_details['total_care_gaps']} (open: {patient_details['open_care_gaps']})")
            print(f"  - Appointments: {patient_details['total_appointments']}")
            
            return True
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_update_patient():
    """Test patient update functionality"""
    print("\n=== Testing Patient Update ===")
    
    try:
        with get_db_session() as session:
            # Get first patient
            patient = session.query(Patient).first()
            if not patient:
                print("✗ No patients found")
                return False
            
            # Store original values
            original_risk_factors = patient.risk_factors
            
            # Update patient
            new_risk_factors = f"Updated risk factors - Test at {patient.id}"
            patient.risk_factors = new_risk_factors
            patient.preferred_contact_method = "email"
            
            session.commit()
            
            print(f"✓ Updated patient {patient.name}:")
            print(f"  - Original risk factors: {original_risk_factors[:50]}...")
            print(f"  - New risk factors: {new_risk_factors}")
            print(f"  - Preferred contact: email")
            
            return True
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def test_close_care_gap():
    """Test care gap closure functionality"""
    print("\n=== Testing Care Gap Closure ===")
    
    try:
        with get_db_session() as session:
            # Find an open care gap
            care_gap = session.query(CareGap).filter(
                CareGap.status == CareGapStatus.OPEN
            ).first()
            
            if not care_gap:
                print("✗ No open care gaps found")
                return False
            
            # Store original values
            original_status = care_gap.status.value
            
            # Close the care gap
            care_gap.status = CareGapStatus.CLOSED
            care_gap.overdue_days = 0
            from datetime import date
            care_gap.last_screening_date = date.today()
            
            session.commit()
            
            patient = session.query(Patient).filter(Patient.id == care_gap.patient_id).first()
            
            print(f"✓ Closed care gap for {patient.name}:")
            print(f"  - Screening type: {care_gap.screening_type}")
            print(f"  - Original status: {original_status}")
            print(f"  - New status: {care_gap.status.value}")
            print(f"  - Completion date: {care_gap.last_screening_date}")
            
            return True
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("="*60)
    print("EHR MCP SERVER CORE FUNCTIONALITY TESTS")
    print("="*60)
    
    tests = [
        test_overdue_patients,
        test_patient_details,
        test_update_patient,
        test_close_care_gap
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print(f"Success rate: {(passed/(passed+failed))*100:.1f}%")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)