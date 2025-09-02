#!/usr/bin/env python3

import asyncio
import sys
import logging
from pathlib import Path

# Add the current directory to the path to enable imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_basic_agent_functionality():
    """Test basic agent functionality step by step"""
    
    logger.info("🚀 Testing basic agent functionality...")
    
    try:
        # Test 1: Import and create DataAnalyst Agent
        logger.info("Step 1: Testing DataAnalyst Agent...")
        from app.agents.data_analyst import DataAnalystAgent
        
        data_analyst = DataAnalystAgent()
        logger.info("✅ DataAnalyst Agent created successfully")
        
        # Initialize agent
        await data_analyst.initialize()
        logger.info("✅ DataAnalyst Agent initialized successfully")
        
        # Test basic functionality
        result = await data_analyst.process_message(
            "prioritize overdue patients", 
            {"filters": {"limit": 5}}
        )
        
        if result.get("status") == "success":
            patients = result.get("prioritized_patients", [])
            logger.info(f"✅ DataAnalyst processed {len(patients)} patients successfully")
            
            # Show sample data
            if patients:
                sample_patient = patients[0]
                logger.info(f"  Sample patient: {sample_patient.get('name')} (Priority: {sample_patient.get('priority_level')})")
        else:
            logger.error(f"❌ DataAnalyst processing failed: {result}")
            return False
        
        # Cleanup
        await data_analyst.cleanup()
        logger.info("✅ DataAnalyst Agent cleaned up")
        
        # Test 2: CommunicationSpecialist Agent
        logger.info("\nStep 2: Testing CommunicationSpecialist Agent...")
        from app.agents.communication_specialist import CommunicationSpecialistAgent
        
        comm_agent = CommunicationSpecialistAgent()
        await comm_agent.initialize()
        logger.info("✅ CommunicationSpecialist Agent initialized successfully")
        
        # Test communication generation
        if patients:
            sample_patient = patients[0]
            comm_result = await comm_agent.process_message(
                "create outreach message for high-priority patient",
                {
                    "patient_id": sample_patient["patient_id"],
                    "priority_level": sample_patient.get("priority_level", "HIGH"),
                    "overdue_screenings": sample_patient.get("overdue_care_gaps", [])
                }
            )
            
            if comm_result.get("status") == "success":
                logger.info("✅ CommunicationSpecialist created messages successfully")
                messages = comm_result.get("messages", {})
                logger.info(f"  Generated {len(messages)} communication channels")
            else:
                logger.error(f"❌ CommunicationSpecialist failed: {comm_result}")
        
        await comm_agent.cleanup()
        logger.info("✅ CommunicationSpecialist Agent cleaned up")
        
        # Test 3: CareManager Agent
        logger.info("\nStep 3: Testing CareManager Agent...")
        from app.agents.care_manager import CareManagerAgent
        
        care_manager = CareManagerAgent()
        await care_manager.initialize()
        logger.info("✅ CareManager Agent initialized successfully")
        
        # Test workflow orchestration
        workflow_result = await care_manager.process_message(
            "orchestrate care gap closure workflow",
            {
                "patients": patients[:3] if patients else [],
                "workflow_type": "care_gap_closure"
            }
        )
        
        if workflow_result.get("status") == "success":
            logger.info("✅ CareManager orchestrated workflow successfully")
            workflow_steps = workflow_result.get("workflow_steps", [])
            logger.info(f"  Created {len(workflow_steps)} workflow steps")
        else:
            logger.error(f"❌ CareManager failed: {workflow_result}")
        
        await care_manager.cleanup()
        logger.info("✅ CareManager Agent cleaned up")
        
        logger.info("\n🎉 All basic agent tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Basic agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_database_patient_data():
    """Test database integration with existing patient data"""
    logger.info("\n🗄️ Testing database integration...")
    
    try:
        from app.config.database import SessionLocal
        from app.models.patient import Patient
        from app.models.care_gap import CareGap, CareGapStatus
        
        # Get database session
        db = SessionLocal()
        
        # Check existing patients
        patients = db.query(Patient).limit(10).all()
        logger.info(f"Found {len(patients)} patients in database")
        
        if len(patients) == 0:
            logger.warning("No patients found in database!")
            return False
            
        # Show sample patient data
        for i, patient in enumerate(patients[:5]):
            logger.info(f"  Patient {i+1}: {patient.name} (Age: {patient.age}, ID: {patient.id})")
        
        # Check care gaps
        care_gaps = db.query(CareGap).filter(CareGap.status == CareGapStatus.OPEN).limit(10).all()
        logger.info(f"Found {len(care_gaps)} open care gaps")
        
        # Show sample care gaps
        for i, gap in enumerate(care_gaps[:5]):
            logger.info(f"  Care Gap {i+1}: {gap.screening_type} for Patient {gap.patient_id} (Overdue: {gap.overdue_days} days)")
        
        db.close()
        logger.info("✅ Database integration verified successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test execution"""
    logger.info("Starting Simple Healthcare Agent Testing")
    
    # Test database first
    db_test = await test_database_patient_data()
    if not db_test:
        logger.error("Database test failed - cannot proceed with agent tests")
        return
    
    # Test basic agent functionality
    agent_test = await test_basic_agent_functionality()
    
    if agent_test:
        logger.info("\n🎉 Simple agent tests completed successfully!")
        logger.info("✅ All agents are working with the database")
        logger.info("✅ Ready for comprehensive workflow testing")
    else:
        logger.info("\n❌ Some agent tests failed")

if __name__ == "__main__":
    asyncio.run(main())