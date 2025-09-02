#!/usr/bin/env python3

"""
Comprehensive test suite for AutoGen Multi-Agent Healthcare System
Tests individual agents, workflows, and FastAPI integration
"""

import asyncio
import json
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any
import time

# Add the app directory to Python path
app_path = Path(__file__).parent / "app"
sys.path.append(str(app_path))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AutoGenSystemTester:
    """Comprehensive test suite for the AutoGen healthcare system"""
    
    def __init__(self):
        self.test_results = {}
        self.workflow_service = None
        self.individual_agents = {}
    
    async def run_all_tests(self):
        """Run the complete test suite"""
        logger.info("Starting AutoGen Multi-Agent System Test Suite")
        print("=" * 80)
        print("AUTOGEN HEALTHCARE MULTI-AGENT SYSTEM TEST SUITE")  
        print("=" * 80)
        
        try:
            # Test 1: Individual Agent Tests
            await self.test_individual_agents()
            
            # Test 2: Workflow Service Tests
            await self.test_workflow_service()
            
            # Test 3: Multi-Agent Workflow Tests
            await self.test_multi_agent_workflows()
            
            # Test 4: Error Handling and Recovery
            await self.test_error_handling()
            
            # Generate final report
            self.generate_final_report()
            
        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def test_individual_agents(self):
        """Test each agent individually"""
        print("\n" + "=" * 60)
        print("INDIVIDUAL AGENT TESTS")
        print("=" * 60)
        
        # Test DataAnalyst Agent
        await self.test_data_analyst_agent()
        
        # Test CommunicationSpecialist Agent
        await self.test_communication_specialist_agent()
        
        # Test CareManager Agent
        await self.test_care_manager_agent()
    
    async def test_data_analyst_agent(self):
        """Test DataAnalyst agent functionality"""
        print("\n--- Testing DataAnalyst Agent ---")
        
        try:
            from agents.data_analyst import DataAnalystAgent
            
            agent = DataAnalystAgent()
            await agent.initialize()
            
            # Test patient prioritization
            context = {
                "filters": {
                    "min_age": 50,
                    "max_age": 80,
                    "limit": 10
                }
            }
            
            start_time = time.time()
            result = await agent.process_message("prioritize overdue patients", context)
            execution_time = time.time() - start_time
            
            # Validate result
            if result.get("status") == "success":
                analysis_data = result.get("prioritized_patients", [])
                insights = result.get("insights", {})
                
                self.test_results["data_analyst"] = {
                    "status": "PASS",
                    "execution_time": round(execution_time, 2),
                    "patients_analyzed": len(analysis_data),
                    "insights_generated": len(insights),
                    "message": f"Successfully analyzed {len(analysis_data)} patients"
                }
                
                print(f"✓ DataAnalyst Agent: PASSED ({execution_time:.2f}s)")
                print(f"  - Analyzed {len(analysis_data)} patients")
                print(f"  - Generated {len(insights)} insights")
                
                if analysis_data:
                    sample_patient = analysis_data[0]
                    print(f"  - Sample priority score: {sample_patient.get('priority_score', 'N/A')}")
                    print(f"  - Sample priority level: {sample_patient.get('priority_level', 'N/A')}")
            
            else:
                self.test_results["data_analyst"] = {
                    "status": "FAIL",
                    "execution_time": round(execution_time, 2),
                    "error": result.get("message", "Unknown error")
                }
                print(f"✗ DataAnalyst Agent: FAILED - {result.get('message')}")
            
            await agent.cleanup()
            
        except Exception as e:
            self.test_results["data_analyst"] = {
                "status": "ERROR",
                "error": str(e)
            }
            print(f"✗ DataAnalyst Agent: ERROR - {str(e)}")
    
    async def test_communication_specialist_agent(self):
        """Test CommunicationSpecialist agent functionality"""
        print("\n--- Testing CommunicationSpecialist Agent ---")
        
        try:
            from agents.communication_specialist import CommunicationSpecialistAgent
            
            agent = CommunicationSpecialistAgent()
            await agent.initialize()
            
            # Test outreach message creation
            context = {
                "patient_id": 1,
                "priority_level": "HIGH",
                "screening_types": ["mammogram"]
            }
            
            start_time = time.time()
            result = await agent.process_message("create outreach message", context)
            execution_time = time.time() - start_time
            
            # Validate result  
            if result.get("status") == "success":
                message_content = result.get("message_content", {})
                follow_up_schedule = result.get("follow_up_schedule", [])
                
                self.test_results["communication_specialist"] = {
                    "status": "PASS",
                    "execution_time": round(execution_time, 2),
                    "message_generated": bool(message_content),
                    "follow_ups_scheduled": len(follow_up_schedule),
                    "message": f"Created personalized message with {len(follow_up_schedule)} follow-ups"
                }
                
                print(f"✓ CommunicationSpecialist Agent: PASSED ({execution_time:.2f}s)")
                print(f"  - Message subject: {message_content.get('subject', 'N/A')[:60]}...")
                print(f"  - Personalization elements: {len(message_content.get('personalization_elements', {}))}")
                print(f"  - Follow-up schedule: {len(follow_up_schedule)} items")
                print(f"  - Channel versions: {len(message_content.get('channel_versions', {}))}")
            
            else:
                self.test_results["communication_specialist"] = {
                    "status": "FAIL", 
                    "execution_time": round(execution_time, 2),
                    "error": result.get("message", "Unknown error")
                }
                print(f"✗ CommunicationSpecialist Agent: FAILED - {result.get('message')}")
            
            await agent.cleanup()
            
        except Exception as e:
            self.test_results["communication_specialist"] = {
                "status": "ERROR",
                "error": str(e)
            }
            print(f"✗ CommunicationSpecialist Agent: ERROR - {str(e)}")
    
    async def test_care_manager_agent(self):
        """Test CareManager agent functionality"""
        print("\n--- Testing CareManager Agent ---")
        
        try:
            from agents.care_manager import CareManagerAgent
            
            agent = CareManagerAgent()
            await agent.initialize()
            
            # Test workflow start
            context = {
                "filters": {
                    "limit": 5
                }
            }
            
            start_time = time.time()
            result = await agent.process_message("start workflow", context)
            execution_time = time.time() - start_time
            
            # Validate result
            if result.get("status") == "success":
                workflow_id = result.get("workflow_id")
                final_report = result.get("final_report", {})
                execution_summary = result.get("execution_summary", {})
                
                self.test_results["care_manager"] = {
                    "status": "PASS",
                    "execution_time": round(execution_time, 2),
                    "workflow_completed": bool(workflow_id),
                    "steps_completed": execution_summary.get("completed_steps", 0),
                    "success_rate": execution_summary.get("success_rate", 0),
                    "message": f"Workflow {workflow_id} completed successfully"
                }
                
                print(f"✓ CareManager Agent: PASSED ({execution_time:.2f}s)")
                print(f"  - Workflow ID: {workflow_id}")
                print(f"  - Steps completed: {execution_summary.get('completed_steps', 0)}")
                print(f"  - Success rate: {execution_summary.get('success_rate', 0):.1f}%")
                
                if final_report:
                    exec_summary = final_report.get("executive_summary", {})
                    print(f"  - Patients analyzed: {exec_summary.get('total_patients_analyzed', 0)}")
                    print(f"  - Communications created: {exec_summary.get('communications_created', 0)}")
            
            else:
                self.test_results["care_manager"] = {
                    "status": "FAIL",
                    "execution_time": round(execution_time, 2), 
                    "error": result.get("message", "Unknown error")
                }
                print(f"✗ CareManager Agent: FAILED - {result.get('message')}")
            
            await agent.cleanup()
            
        except Exception as e:
            self.test_results["care_manager"] = {
                "status": "ERROR",
                "error": str(e)
            }
            print(f"✗ CareManager Agent: ERROR - {str(e)}")
    
    async def test_workflow_service(self):
        """Test the AutoGen Workflow Service"""
        print("\n" + "=" * 60)
        print("WORKFLOW SERVICE TESTS")
        print("=" * 60)
        
        try:
            from agents.workflow_service import AutoGenWorkflowService
            
            self.workflow_service = AutoGenWorkflowService()
            await self.workflow_service.start_service()
            
            # Test service initialization
            print("\n--- Testing Service Initialization ---")
            
            # Get service metrics
            metrics = await self.workflow_service.get_agent_metrics()
            
            if metrics.get("status") == "success":
                agent_metrics = metrics.get("agent_metrics", {})
                online_agents = len([
                    agent for agent, data in agent_metrics.items() 
                    if data.get("status") in ["idle", "busy"]
                ])
                
                print(f"✓ Workflow Service: INITIALIZED")
                print(f"  - Agents online: {online_agents}/3")
                print(f"  - Service status: {metrics.get('service_status')}")
                
                self.test_results["workflow_service_init"] = {
                    "status": "PASS",
                    "agents_online": online_agents,
                    "service_status": metrics.get("service_status")
                }
            else:
                print(f"✗ Workflow Service: FAILED TO INITIALIZE")
                self.test_results["workflow_service_init"] = {
                    "status": "FAIL",
                    "error": "Service initialization failed"
                }
            
            # Test workflow templates
            print("\n--- Testing Workflow Templates ---")
            templates = self.workflow_service.get_available_templates()
            
            if templates.get("status") == "success":
                available_templates = templates.get("available_templates", {})
                print(f"✓ Workflow Templates: {len(available_templates)} available")
                
                for name, info in available_templates.items():
                    print(f"  - {name}: {info['description'][:50]}...")
                
                self.test_results["workflow_templates"] = {
                    "status": "PASS", 
                    "templates_count": len(available_templates),
                    "template_names": list(available_templates.keys())
                }
            else:
                print(f"✗ Workflow Templates: FAILED TO LOAD")
                self.test_results["workflow_templates"] = {
                    "status": "FAIL",
                    "error": "Templates loading failed"
                }
            
        except Exception as e:
            print(f"✗ Workflow Service: ERROR - {str(e)}")
            self.test_results["workflow_service"] = {
                "status": "ERROR",
                "error": str(e)
            }
    
    async def test_multi_agent_workflows(self):
        """Test multi-agent workflow execution"""
        print("\n" + "=" * 60)
        print("MULTI-AGENT WORKFLOW TESTS")
        print("=" * 60)
        
        if not self.workflow_service:
            print("✗ Skipping workflow tests - service not initialized")
            return
        
        # Test care gap automation workflow
        await self.test_care_gap_workflow()
        
        # Test urgent patient workflow
        await self.test_urgent_workflow()
        
        # Test population analysis workflow
        await self.test_population_analysis_workflow()
    
    async def test_care_gap_workflow(self):
        """Test complete care gap automation workflow"""
        print("\n--- Testing Care Gap Automation Workflow ---")
        
        try:
            context = {
                "filters": {
                    "min_age": 40,
                    "limit": 5
                },
                "workflow_options": {
                    "priority_threshold": "medium"
                }
            }
            
            start_time = time.time()
            result = await self.workflow_service.start_workflow(
                "care_gap_automation",
                context
            )
            execution_time = time.time() - start_time
            
            if result.get("status") == "success":
                workflow_id = result.get("workflow_id")
                execution_result = result.get("execution_result", {})
                
                print(f"✓ Care Gap Workflow: COMPLETED ({execution_time:.2f}s)")
                print(f"  - Workflow ID: {workflow_id}")
                print(f"  - Execution status: {execution_result.get('status')}")
                print(f"  - Steps completed: {execution_result.get('steps_completed', 0)}")
                
                step_results = execution_result.get("step_results", {})
                if "analyze_patients" in step_results:
                    analysis = step_results["analyze_patients"]
                    insights = analysis.get("insights", {})
                    print(f"  - Patients analyzed: {insights.get('total_patients', 0)}")
                    print(f"  - Critical patients: {insights.get('critical_patients', 0)}")
                
                if "create_communications" in step_results:
                    comm = step_results["create_communications"]
                    print(f"  - Communications created: {comm.get('total_created', 0)}")
                
                self.test_results["care_gap_workflow"] = {
                    "status": "PASS",
                    "execution_time": round(execution_time, 2),
                    "workflow_id": workflow_id,
                    "steps_completed": execution_result.get("steps_completed", 0)
                }
            
            else:
                print(f"✗ Care Gap Workflow: FAILED - {result.get('message')}")
                self.test_results["care_gap_workflow"] = {
                    "status": "FAIL",
                    "error": result.get("message"),
                    "execution_time": round(execution_time, 2)
                }
            
        except Exception as e:
            print(f"✗ Care Gap Workflow: ERROR - {str(e)}")
            self.test_results["care_gap_workflow"] = {
                "status": "ERROR",
                "error": str(e)
            }
    
    async def test_urgent_workflow(self):
        """Test urgent patient workflow"""
        print("\n--- Testing Urgent Patient Workflow ---")
        
        try:
            context = {
                "filters": {
                    "priority_level": "urgent",
                    "limit": 3
                }
            }
            
            start_time = time.time()
            result = await self.workflow_service.start_workflow(
                "urgent_patient_outreach",
                context
            )
            execution_time = time.time() - start_time
            
            if result.get("status") == "success":
                print(f"✓ Urgent Workflow: COMPLETED ({execution_time:.2f}s)")
                
                self.test_results["urgent_workflow"] = {
                    "status": "PASS",
                    "execution_time": round(execution_time, 2)
                }
            else:
                print(f"✗ Urgent Workflow: FAILED - {result.get('message')}")
                self.test_results["urgent_workflow"] = {
                    "status": "FAIL",
                    "error": result.get("message")
                }
            
        except Exception as e:
            print(f"✗ Urgent Workflow: ERROR - {str(e)}")
            self.test_results["urgent_workflow"] = {
                "status": "ERROR", 
                "error": str(e)
            }
    
    async def test_population_analysis_workflow(self):
        """Test population analysis workflow"""
        print("\n--- Testing Population Analysis Workflow ---")
        
        try:
            context = {
                "analysis_type": "demographic_breakdown",
                "filters": {
                    "limit": 20
                }
            }
            
            start_time = time.time()
            result = await self.workflow_service.start_workflow(
                "population_analysis",
                context
            )
            execution_time = time.time() - start_time
            
            if result.get("status") in ["success", "partial_success"]:
                print(f"✓ Population Analysis: COMPLETED ({execution_time:.2f}s)")
                
                self.test_results["population_analysis"] = {
                    "status": "PASS",
                    "execution_time": round(execution_time, 2),
                    "result_status": result.get("status")
                }
            else:
                print(f"✗ Population Analysis: FAILED - {result.get('message')}")
                self.test_results["population_analysis"] = {
                    "status": "FAIL",
                    "error": result.get("message")
                }
            
        except Exception as e:
            print(f"✗ Population Analysis: ERROR - {str(e)}")
            self.test_results["population_analysis"] = {
                "status": "ERROR",
                "error": str(e)
            }
    
    async def test_error_handling(self):
        """Test error handling and recovery mechanisms"""
        print("\n" + "=" * 60)
        print("ERROR HANDLING TESTS")
        print("=" * 60)
        
        if not self.workflow_service:
            print("✗ Skipping error handling tests - service not initialized")
            return
        
        # Test invalid workflow template
        print("\n--- Testing Invalid Workflow Template ---")
        try:
            result = await self.workflow_service.start_workflow(
                "nonexistent_workflow",
                {}
            )
            
            if result.get("status") == "error":
                print("✓ Invalid template handling: PASSED")
                self.test_results["error_invalid_template"] = {"status": "PASS"}
            else:
                print("✗ Invalid template handling: FAILED")
                self.test_results["error_invalid_template"] = {"status": "FAIL"}
                
        except Exception as e:
            print(f"✓ Invalid template handling: PASSED (exception caught: {type(e).__name__})")
            self.test_results["error_invalid_template"] = {"status": "PASS"}
        
        # Test concurrent workflow limits  
        print("\n--- Testing Concurrent Workflow Limits ---")
        try:
            # This test would require starting multiple workflows simultaneously
            # For now, just verify the service tracks concurrent workflows correctly
            status = await self.workflow_service.get_workflow_status()
            
            if status.get("status") == "success":
                print("✓ Workflow status monitoring: PASSED")
                self.test_results["error_monitoring"] = {"status": "PASS"}
            else:
                print("✗ Workflow status monitoring: FAILED")
                self.test_results["error_monitoring"] = {"status": "FAIL"}
                
        except Exception as e:
            print(f"✗ Workflow monitoring: ERROR - {str(e)}")
            self.test_results["error_monitoring"] = {"status": "ERROR", "error": str(e)}
    
    def generate_final_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("FINAL TEST REPORT")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r.get("status") == "PASS"])
        failed_tests = len([r for r in self.test_results.values() if r.get("status") == "FAIL"])
        error_tests = len([r for r in self.test_results.values() if r.get("status") == "ERROR"])
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Errors: {error_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n" + "-" * 80)
        print("DETAILED RESULTS:")
        print("-" * 80)
        
        for test_name, result in self.test_results.items():
            status_icon = "✓" if result["status"] == "PASS" else "✗" if result["status"] == "FAIL" else "!"
            
            print(f"{status_icon} {test_name.upper().replace('_', ' ')}: {result['status']}")
            
            if "execution_time" in result:
                print(f"   Execution Time: {result['execution_time']}s")
            
            if "message" in result:
                print(f"   Details: {result['message']}")
            
            if "error" in result:
                print(f"   Error: {result['error']}")
            
            print()
        
        print("=" * 80)
        
        # Cleanup
        if self.workflow_service:
            asyncio.create_task(self.workflow_service.stop_service())
        
        return passed_tests == total_tests


async def main():
    """Main test runner"""
    tester = AutoGenSystemTester()
    
    try:
        success = await tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nTest suite crashed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())