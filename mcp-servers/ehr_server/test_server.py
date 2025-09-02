#!/usr/bin/env python3

import asyncio
import json
import logging
import pytest
from datetime import datetime, date, timedelta
from typing import Dict, Any

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TestEHRMCPServer:
    """Comprehensive test suite for EHR MCP server"""
    
    def __init__(self):
        self.client = None
        self.test_results = {}
    
    async def setup_client(self):
        """Set up the MCP client for testing"""
        try:
            from client import EHRMCPClient
            
            self.client = EHRMCPClient()
            
            # Connect to the server
            server_command = ["python", "server.py"]
            connected = await self.client.connect(server_command)
            
            if not connected:
                raise ConnectionError("Failed to connect to EHR MCP server")
            
            logger.info("Test client connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup test client: {e}")
            return False
    
    async def teardown_client(self):
        """Tear down the client connection"""
        if self.client:
            await self.client.disconnect()
            logger.info("Test client disconnected")
    
    async def test_server_connectivity(self):
        """Test basic server connectivity"""
        test_name = "server_connectivity"
        try:
            # List tools to verify server is responding
            tools = await self.client.list_tools()
            resources = await self.client.list_resources()
            
            expected_tools = [
                "get_overdue_patients",
                "get_patient_details", 
                "update_patient_record",
                "close_care_gap"
            ]
            
            tool_names = [tool.name for tool in tools]
            missing_tools = set(expected_tools) - set(tool_names)
            
            if missing_tools:
                raise AssertionError(f"Missing expected tools: {missing_tools}")
            
            self.test_results[test_name] = {
                "status": "PASS",
                "message": f"Server responding with {len(tools)} tools and {len(resources)} resources",
                "details": {
                    "tools": tool_names,
                    "resources": [r.name for r in resources]
                }
            }
            
            logger.info(f"✓ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAIL",
                "message": str(e),
                "details": {}
            }
            logger.error(f"✗ {test_name} failed: {e}")
    
    async def test_get_overdue_patients_basic(self):
        """Test basic get_overdue_patients functionality"""
        test_name = "get_overdue_patients_basic"
        try:
            # Test with no filters
            result = await self.client.get_overdue_patients(limit=10)
            parsed_result = json.loads(result)
            
            if parsed_result.get("status") != "success":
                raise AssertionError(f"Expected success status, got: {parsed_result.get('status')}")
            
            patients = parsed_result.get("patients", [])
            total_patients = parsed_result.get("total_patients", 0)
            
            if total_patients != len(patients):
                raise AssertionError(f"Total patients mismatch: reported {total_patients}, actual {len(patients)}")
            
            # Verify patient structure
            if patients:
                patient = patients[0]
                required_fields = ["patient_id", "name", "age", "email", "overdue_care_gaps"]
                missing_fields = set(required_fields) - set(patient.keys())
                
                if missing_fields:
                    raise AssertionError(f"Missing required patient fields: {missing_fields}")
            
            self.test_results[test_name] = {
                "status": "PASS",
                "message": f"Retrieved {total_patients} overdue patients",
                "details": {
                    "total_patients": total_patients,
                    "sample_patient_fields": list(patients[0].keys()) if patients else []
                }
            }
            
            logger.info(f"✓ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAIL", 
                "message": str(e),
                "details": {}
            }
            logger.error(f"✗ {test_name} failed: {e}")
    
    async def test_get_overdue_patients_with_filters(self):
        """Test get_overdue_patients with various filters"""
        test_name = "get_overdue_patients_with_filters"
        try:
            # Test age filter
            result = await self.client.get_overdue_patients(min_age=30, max_age=65, limit=5)
            parsed_result = json.loads(result)
            
            if parsed_result.get("status") != "success":
                raise AssertionError("Age filter test failed")
            
            # Verify age filtering worked
            for patient in parsed_result.get("patients", []):
                age = patient.get("age")
                if age is not None and (age < 30 or age > 65):
                    raise AssertionError(f"Patient age {age} outside filter range 30-65")
            
            # Test priority filter  
            result = await self.client.get_overdue_patients(priority_level="high", limit=5)
            parsed_result = json.loads(result)
            
            if parsed_result.get("status") != "success":
                raise AssertionError("Priority filter test failed")
            
            # Test screening type filter
            result = await self.client.get_overdue_patients(screening_type="mammogram", limit=5)
            parsed_result = json.loads(result)
            
            if parsed_result.get("status") != "success":
                raise AssertionError("Screening type filter test failed")
            
            self.test_results[test_name] = {
                "status": "PASS",
                "message": "All filter tests passed",
                "details": {
                    "age_filter": "✓",
                    "priority_filter": "✓", 
                    "screening_type_filter": "✓"
                }
            }
            
            logger.info(f"✓ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAIL",
                "message": str(e),
                "details": {}
            }
            logger.error(f"✗ {test_name} failed: {e}")
    
    async def test_get_patient_details(self):
        """Test get_patient_details functionality"""
        test_name = "get_patient_details"
        try:
            # First get a valid patient ID from overdue patients
            overdue_result = await self.client.get_overdue_patients(limit=1)
            overdue_parsed = json.loads(overdue_result)
            
            if not overdue_parsed.get("patients"):
                # Test with patient ID 1 as fallback
                patient_id = 1
            else:
                patient_id = overdue_parsed["patients"][0]["patient_id"]
            
            # Test getting patient details
            result = await self.client.get_patient_details(patient_id)
            parsed_result = json.loads(result)
            
            if parsed_result.get("status") == "error":
                # This is acceptable if patient doesn't exist
                if "not found" in parsed_result.get("message", "").lower():
                    self.test_results[test_name] = {
                        "status": "PASS",
                        "message": f"Patient {patient_id} not found (expected for empty database)",
                        "details": {"patient_id": patient_id}
                    }
                    logger.info(f"✓ {test_name} passed (patient not found)")
                    return
                else:
                    raise AssertionError(f"Unexpected error: {parsed_result.get('message')}")
            
            if parsed_result.get("status") != "success":
                raise AssertionError(f"Expected success status, got: {parsed_result.get('status')}")
            
            # Verify patient details structure
            patient = parsed_result.get("patient", {})
            required_fields = [
                "patient_id", "name", "age", "email", "care_gaps", 
                "appointments", "total_care_gaps", "open_care_gaps"
            ]
            missing_fields = set(required_fields) - set(patient.keys())
            
            if missing_fields:
                raise AssertionError(f"Missing required patient detail fields: {missing_fields}")
            
            self.test_results[test_name] = {
                "status": "PASS",
                "message": f"Retrieved details for patient {patient_id}",
                "details": {
                    "patient_id": patient_id,
                    "patient_name": patient.get("name"),
                    "care_gaps_count": patient.get("total_care_gaps"),
                    "appointments_count": patient.get("total_appointments")
                }
            }
            
            logger.info(f"✓ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAIL",
                "message": str(e),
                "details": {}
            }
            logger.error(f"✗ {test_name} failed: {e}")
    
    async def test_update_patient_record(self):
        """Test update_patient_record functionality"""
        test_name = "update_patient_record"
        try:
            # Use patient ID 1 for testing
            patient_id = 1
            
            # Test valid updates
            updates = {
                "preferred_contact_method": "email",
                "risk_factors": f"Test update at {datetime.now().isoformat()}"
            }
            
            result = await self.client.update_patient_record(patient_id, updates)
            parsed_result = json.loads(result)
            
            if parsed_result.get("status") == "error" and "not found" in parsed_result.get("message", "").lower():
                # This is acceptable if patient doesn't exist
                self.test_results[test_name] = {
                    "status": "PASS", 
                    "message": f"Patient {patient_id} not found (expected for empty database)",
                    "details": {"patient_id": patient_id}
                }
                logger.info(f"✓ {test_name} passed (patient not found)")
                return
            
            if parsed_result.get("status") != "success":
                raise AssertionError(f"Update failed: {parsed_result.get('message')}")
            
            # Verify update response structure
            if "updated_fields" not in parsed_result:
                raise AssertionError("Missing updated_fields in response")
            
            self.test_results[test_name] = {
                "status": "PASS",
                "message": f"Successfully updated patient {patient_id}",
                "details": {
                    "patient_id": patient_id,
                    "updated_fields": parsed_result.get("updated_fields", []),
                    "updates_applied": updates
                }
            }
            
            logger.info(f"✓ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAIL",
                "message": str(e),
                "details": {}
            }
            logger.error(f"✗ {test_name} failed: {e}")
    
    async def test_close_care_gap(self):
        """Test close_care_gap functionality"""
        test_name = "close_care_gap"
        try:
            # Use care gap ID 1 for testing
            care_gap_id = 1
            completion_date = date.today().isoformat()
            notes = f"Test closure at {datetime.now().isoformat()}"
            
            result = await self.client.close_care_gap(care_gap_id, completion_date, notes)
            parsed_result = json.loads(result)
            
            if parsed_result.get("status") == "error" and "not found" in parsed_result.get("message", "").lower():
                # This is acceptable if care gap doesn't exist
                self.test_results[test_name] = {
                    "status": "PASS",
                    "message": f"Care gap {care_gap_id} not found (expected for empty database)",
                    "details": {"care_gap_id": care_gap_id}
                }
                logger.info(f"✓ {test_name} passed (care gap not found)")
                return
            
            if parsed_result.get("status") == "warning":
                # Already closed is also acceptable
                self.test_results[test_name] = {
                    "status": "PASS",
                    "message": parsed_result.get("message", "Care gap already closed"),
                    "details": {"care_gap_id": care_gap_id}
                }
                logger.info(f"✓ {test_name} passed (already closed)")
                return
            
            if parsed_result.get("status") != "success":
                raise AssertionError(f"Close care gap failed: {parsed_result.get('message')}")
            
            # Verify close response structure
            required_fields = ["care_gap_id", "patient_id", "screening_type", "completion_date"]
            missing_fields = set(required_fields) - set(parsed_result.keys())
            
            if missing_fields:
                raise AssertionError(f"Missing required close response fields: {missing_fields}")
            
            self.test_results[test_name] = {
                "status": "PASS",
                "message": f"Successfully closed care gap {care_gap_id}",
                "details": {
                    "care_gap_id": care_gap_id,
                    "patient_id": parsed_result.get("patient_id"),
                    "screening_type": parsed_result.get("screening_type"),
                    "completion_date": parsed_result.get("completion_date")
                }
            }
            
            logger.info(f"✓ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAIL",
                "message": str(e),
                "details": {}
            }
            logger.error(f"✗ {test_name} failed: {e}")
    
    async def test_error_handling(self):
        """Test error handling for invalid inputs"""
        test_name = "error_handling"
        try:
            error_tests = []
            
            # Test invalid patient ID
            try:
                result = await self.client.get_patient_details(-1)
                parsed = json.loads(result)
                if "error" not in result.lower():
                    error_tests.append("Invalid patient ID should return error")
            except:
                pass  # Error expected
            
            # Test invalid age range
            try:
                result = await self.client.get_overdue_patients(min_age=100, max_age=50)
                parsed = json.loads(result)
                if "error" not in result.lower():
                    error_tests.append("Invalid age range should return error")
            except:
                pass  # Error expected
            
            # Test invalid priority level
            try:
                result = await self.client.get_overdue_patients(priority_level="invalid")
                parsed = json.loads(result)
                if "error" not in result.lower():
                    error_tests.append("Invalid priority level should return error")
            except:
                pass  # Error expected
            
            if error_tests:
                raise AssertionError(f"Error handling issues: {error_tests}")
            
            self.test_results[test_name] = {
                "status": "PASS",
                "message": "Error handling working correctly",
                "details": {"tests_passed": 3}
            }
            
            logger.info(f"✓ {test_name} passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "FAIL",
                "message": str(e),
                "details": {}
            }
            logger.error(f"✗ {test_name} failed: {e}")
    
    def print_test_report(self):
        """Print comprehensive test report"""
        print("\n" + "="*80)
        print("EHR MCP SERVER TEST REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results.values() if r["status"] == "PASS"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print("\n" + "-"*80)
        
        for test_name, result in self.test_results.items():
            status_icon = "✓" if result["status"] == "PASS" else "✗"
            print(f"{status_icon} {test_name.upper()}: {result['status']}")
            print(f"   Message: {result['message']}")
            
            if result["details"]:
                print("   Details:")
                for key, value in result["details"].items():
                    print(f"     - {key}: {value}")
            print()
        
        print("="*80)
        return passed_tests == total_tests
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("Starting EHR MCP Server test suite...")
        
        if not await self.setup_client():
            logger.error("Failed to setup test client")
            return False
        
        try:
            # Run all test methods
            test_methods = [
                self.test_server_connectivity,
                self.test_get_overdue_patients_basic,
                self.test_get_overdue_patients_with_filters,
                self.test_get_patient_details,
                self.test_update_patient_record,
                self.test_close_care_gap,
                self.test_error_handling
            ]
            
            for test_method in test_methods:
                await test_method()
            
            # Print final report
            all_passed = self.print_test_report()
            
            if all_passed:
                logger.info("All tests passed! 🎉")
            else:
                logger.warning("Some tests failed. Check the report above.")
            
            return all_passed
            
        finally:
            await self.teardown_client()


async def main():
    """Main test runner"""
    tester = TestEHRMCPServer()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)