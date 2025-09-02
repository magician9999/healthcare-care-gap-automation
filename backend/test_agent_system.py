#!/usr/bin/env python3

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add the current directory to the path to enable imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from app.agents.data_analyst import DataAnalystAgent
from app.agents.communication_specialist import CommunicationSpecialistAgent
from app.agents.care_manager import CareManagerAgent
from app.agents.workflow_service import AutoGenWorkflowService
from app.config.database import SessionLocal, create_tables
from app.models.patient import Patient
from app.models.care_gap import CareGap, CareGapStatus

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthcareSystemTester:
    """Comprehensive tester for the healthcare AutoGen system"""
    
    def __init__(self):
        self.data_analyst = None
        self.communication_specialist = None
        self.care_manager = None
        self.workflow_service = None
        
    async def test_individual_agent_initialization(self):
        """Test 1: Individual agent initialization and MCP connections"""
        logger.info("🔍 Testing individual agent initialization...")
        
        try:
            # Test DataAnalyst Agent
            logger.info("Initializing DataAnalyst Agent...")
            self.data_analyst = DataAnalystAgent()
            await self.data_analyst.initialize()
            logger.info("✅ DataAnalyst Agent initialized successfully")
            
            # Test CommunicationSpecialist Agent  
            logger.info("Initializing CommunicationSpecialist Agent...")
            self.communication_specialist = CommunicationSpecialistAgent()
            await self.communication_specialist.initialize()
            logger.info("✅ CommunicationSpecialist Agent initialized successfully")
            
            # Test CareManager Agent
            logger.info("Initializing CareManager Agent...")
            self.care_manager = CareManagerAgent()
            await self.care_manager.initialize()
            logger.info("✅ CareManager Agent initialized successfully")
            
            logger.info("🎉 All agents initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Agent initialization failed: {e}")
            return False
    
    async def test_database_integration(self):
        """Test 2: Database integration with existing patient data"""
        logger.info("🗄️ Testing database integration...")
        
        try:
            # Get database session
            db = SessionLocal()
            
            # Check existing patients
            patients = db.query(Patient).limit(20).all()
            logger.info(f"Found {len(patients)} patients in database")
            
            if len(patients) == 0:
                logger.warning("No patients found in database!")
                return False
                
            # Check care gaps
            care_gaps = db.query(CareGap).filter(CareGap.status == CareGapStatus.OPEN).limit(10).all()
            logger.info(f"Found {len(care_gaps)} open care gaps")
            
            # Test data analyst with real data
            if self.data_analyst:
                logger.info("Testing DataAnalyst with real patient data...")
                result = await self.data_analyst.process_message(
                    "prioritize overdue patients",
                    {"filters": {"limit": 5}}
                )
                
                if result.get("status") == "success":
                    logger.info(f"✅ Successfully prioritized {result.get('total_patients', 0)} patients")
                    # Display sample results
                    for patient in result.get("prioritized_patients", [])[:3]:
                        logger.info(f"  Patient {patient['name']} (ID: {patient['patient_id']}) - Priority: {patient.get('priority_level', 'N/A')}")
                else:
                    logger.error(f"❌ DataAnalyst prioritization failed: {result.get('message')}")
                    return False
            
            db.close()
            logger.info("✅ Database integration test passed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database integration test failed: {e}")
            return False
    
    async def test_workflow_service_initialization(self):
        """Test 3: WorkflowService initialization and orchestration"""
        logger.info("🔧 Testing Workflow Service initialization...")
        
        try:
            self.workflow_service = AutoGenWorkflowService()
            await self.workflow_service.start_service()
            logger.info("✅ Workflow Service initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Workflow Service initialization failed: {e}")
            return False
    
    async def test_care_gap_closure_workflow(self):
        """Test 4: Complete care-gap closure workflow (Identify → Analyze → Prioritize → Report)"""
        logger.info("🏥 Testing complete care-gap closure workflow...")
        
        try:
            # Step 1: Identify - Get overdue patients
            logger.info("Step 1: Identifying overdue patients...")
            identify_result = await self.data_analyst.process_message(
                "get overdue patients for analysis",
                {"filters": {"limit": 10}}
            )
            
            if identify_result.get("status") != "success":
                logger.error("❌ Failed to identify overdue patients")
                return False
                
            patients = identify_result.get("prioritized_patients", [])
            logger.info(f"✅ Identified {len(patients)} overdue patients")
            
            # Step 2: Analyze - Detailed priority analysis
            if patients:
                logger.info("Step 2: Analyzing patient priorities...")
                sample_patient = patients[0]
                analysis_result = await self.data_analyst.process_message(
                    "perform risk assessment",
                    {"patient_id": sample_patient["patient_id"]}
                )
                
                if analysis_result.get("status") == "success":
                    logger.info(f"✅ Analysis completed for patient {sample_patient['name']}")
                    risk_assessment = analysis_result.get("risk_assessment", {})
                    logger.info(f"  Priority Level: {risk_assessment.get('priority_level')}")
                    logger.info(f"  Total Score: {risk_assessment.get('total_score')}")
                else:
                    logger.error("❌ Patient risk analysis failed")
                    return False
            
            # Step 3: Prioritize - Create communication strategy
            logger.info("Step 3: Creating communication strategy...")
            if patients:
                top_patient = patients[0]
                comm_result = await self.communication_specialist.process_message(
                    "create outreach message for high-priority patient",
                    {
                        "patient_id": top_patient["patient_id"],
                        "priority_level": top_patient.get("priority_level", "HIGH"),
                        "overdue_screenings": top_patient.get("overdue_care_gaps", [])
                    }
                )
                
                if comm_result.get("status") == "success":
                    logger.info("✅ Communication strategy created")
                    messages = comm_result.get("messages", {})
                    logger.info(f"  Generated {len(messages)} communication messages")
                else:
                    logger.error("❌ Communication strategy creation failed")
                    return False
            
            # Step 4: Report - Workflow management
            logger.info("Step 4: Workflow orchestration and reporting...")
            workflow_result = await self.care_manager.process_message(
                "orchestrate care gap closure workflow",
                {
                    "patients": patients[:3],  # Process top 3 patients
                    "workflow_type": "care_gap_closure"
                }
            )
            
            if workflow_result.get("status") == "success":
                logger.info("✅ Workflow orchestration completed")
                workflow_steps = workflow_result.get("workflow_steps", [])
                logger.info(f"  Created {len(workflow_steps)} workflow steps")
            else:
                logger.error("❌ Workflow orchestration failed")
                return False
            
            logger.info("🎉 Complete care-gap closure workflow tested successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Care-gap closure workflow test failed: {e}")
            return False
    
    async def test_multi_agent_collaboration(self):
        """Test 5: Multi-agent collaboration with proper handoffs"""
        logger.info("🤝 Testing multi-agent collaboration...")
        
        try:
            if not self.workflow_service:
                logger.error("Workflow service not initialized")
                return False
            
            # Test collaborative workflow
            workflow_config = {
                "workflow_id": "test_collaboration",
                "execution_pattern": "SEQUENTIAL",
                "steps": [
                    {
                        "step_id": "analyze_patients",
                        "agent_name": "data_analyst",
                        "message": "prioritize overdue patients", 
                        "context": {"filters": {"limit": 5}}
                    },
                    {
                        "step_id": "create_communications",
                        "agent_name": "communication_specialist", 
                        "message": "create personalized outreach messages",
                        "context": {"batch_processing": True}
                    },
                    {
                        "step_id": "manage_workflow",
                        "agent_name": "care_manager",
                        "message": "coordinate care team actions",
                        "context": {"workflow_type": "patient_outreach"}
                    }
                ]
            }
            
            # Execute collaborative workflow
            logger.info("Executing multi-agent workflow...")
            result = await self.workflow_service.start_workflow(
                "care_gap_automation", 
                {"filters": {"limit": 3}}
            )
            
            if result.get("status") == "success":
                logger.info("✅ Multi-agent collaboration successful")
                execution_result = result.get("execution_result", {})
                step_results = execution_result.get("step_results", {})
                logger.info(f"  Completed {len(step_results)} workflow steps")
                
                # Check handoffs between agents
                for step_name, step_result in step_results.items():
                    logger.info(f"  Step {step_name}: {step_result.get('status', 'unknown')}")
                    
            else:
                logger.error(f"❌ Multi-agent collaboration failed: {result.get('message')}")
                return False
            
            logger.info("🎉 Multi-agent collaboration tested successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Multi-agent collaboration test failed: {e}")
            return False
    
    async def test_healthcare_scenarios(self):
        """Test 6: Realistic healthcare scenarios using existing patient data"""
        logger.info("🏥 Testing realistic healthcare scenarios...")
        
        try:
            # Scenario 1: Critical patient prioritization
            logger.info("Scenario 1: Critical patient prioritization...")
            critical_result = await self.data_analyst.process_message(
                "identify critical patients requiring immediate intervention",
                {"filters": {"limit": 20}}
            )
            
            critical_patients = []
            if critical_result.get("status") == "success":
                critical_patients = [
                    p for p in critical_result.get("prioritized_patients", [])
                    if p.get("priority_level") in ["CRITICAL", "HIGH"]
                ]
                logger.info(f"✅ Identified {len(critical_patients)} critical/high-priority patients")
            
            # Scenario 2: Bulk communication generation
            logger.info("Scenario 2: Bulk patient communication...")
            if critical_patients:
                bulk_comm_result = await self.communication_specialist.process_message(
                    "generate bulk outreach campaign",
                    {
                        "patients": critical_patients[:5],
                        "campaign_type": "care_gap_closure"
                    }
                )
                
                if bulk_comm_result.get("status") == "success":
                    logger.info("✅ Bulk communication campaign created")
                    
            # Scenario 3: Care coordination
            logger.info("Scenario 3: Care coordination workflow...")
            coordination_result = await self.care_manager.process_message(
                "coordinate comprehensive care for high-risk patients",
                {
                    "patients": critical_patients[:3] if critical_patients else [],
                    "coordination_type": "comprehensive_care"
                }
            )
            
            if coordination_result.get("status") == "success":
                logger.info("✅ Care coordination workflow created")
            
            logger.info("🎉 Healthcare scenarios tested successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Healthcare scenarios test failed: {e}")
            return False
    
    async def cleanup_agents(self):
        """Cleanup all agent connections"""
        logger.info("🧹 Cleaning up agents...")
        
        try:
            if self.data_analyst:
                await self.data_analyst.cleanup()
            if self.communication_specialist:
                await self.communication_specialist.cleanup()
            if self.care_manager:
                await self.care_manager.cleanup()
            if self.workflow_service:
                await self.workflow_service.stop_service()
                
            logger.info("✅ All agents cleaned up successfully")
            
        except Exception as e:
            logger.error(f"❌ Agent cleanup failed: {e}")
    
    async def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        logger.info("🚀 Starting comprehensive healthcare AutoGen system tests...")
        
        test_results = []
        
        # Test 1: Individual agent initialization
        result1 = await self.test_individual_agent_initialization()
        test_results.append(("Individual Agent Initialization", result1))
        
        if result1:
            # Test 2: Database integration
            result2 = await self.test_database_integration()
            test_results.append(("Database Integration", result2))
            
            # Test 3: Workflow service
            result3 = await self.test_workflow_service_initialization()
            test_results.append(("Workflow Service Initialization", result3))
            
            if result3:
                # Test 4: Care gap closure workflow
                result4 = await self.test_care_gap_closure_workflow()
                test_results.append(("Care Gap Closure Workflow", result4))
                
                # Test 5: Multi-agent collaboration
                result5 = await self.test_multi_agent_collaboration()
                test_results.append(("Multi-Agent Collaboration", result5))
                
                # Test 6: Healthcare scenarios
                result6 = await self.test_healthcare_scenarios()
                test_results.append(("Healthcare Scenarios", result6))
        
        # Cleanup
        await self.cleanup_agents()
        
        # Report results
        logger.info("\n" + "="*60)
        logger.info("🔍 COMPREHENSIVE TEST RESULTS")
        logger.info("="*60)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\nOverall Results: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 ALL TESTS PASSED! Healthcare AutoGen system is ready!")
        else:
            logger.info("⚠️ Some tests failed. Please review and fix issues.")
        
        return passed == total


async def main():
    """Main test execution"""
    logger.info("Starting Healthcare AutoGen System Testing")
    
    # Ensure database tables exist
    try:
        create_tables()
        logger.info("Database tables verified/created")
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        return
    
    # Run comprehensive tests
    tester = HealthcareSystemTester()
    success = await tester.run_comprehensive_tests()
    
    if success:
        logger.info("🎉 Healthcare AutoGen system is fully operational!")
    else:
        logger.info("❌ System testing completed with issues.")


if __name__ == "__main__":
    asyncio.run(main())