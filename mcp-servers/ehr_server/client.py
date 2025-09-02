#!/usr/bin/env python3

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EHRMCPClient:
    """MCP Client for testing EHR server functionality"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        
    async def connect(self, server_command: list[str]):
        """Connect to the MCP EHR server"""
        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command=server_command[0],
                args=server_command[1:] if len(server_command) > 1 else [],
            )
            
            # Connect to server
            self.session = await stdio_client(server_params)
            
            # Initialize the session
            await self.session.initialize()
            
            logger.info("Successfully connected to EHR MCP server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to EHR server: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from EHR MCP server")
    
    async def list_tools(self):
        """List available tools"""
        if not self.session:
            raise ValueError("Not connected to server")
            
        tools = await self.session.list_tools()
        logger.info(f"Available tools: {[tool.name for tool in tools.tools]}")
        return tools.tools
    
    async def list_resources(self):
        """List available resources"""
        if not self.session:
            raise ValueError("Not connected to server")
            
        resources = await self.session.list_resources()
        logger.info(f"Available resources: {[resource.name for resource in resources.resources]}")
        return resources.resources
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None):
        """Call a tool with given arguments"""
        if not self.session:
            raise ValueError("Not connected to server")
            
        if arguments is None:
            arguments = {}
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            
            # Extract text content from result
            response_text = ""
            for content in result.content:
                if hasattr(content, 'text'):
                    response_text += content.text
                    
            logger.info(f"Tool {tool_name} executed successfully")
            return response_text
            
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            raise
    
    async def get_overdue_patients(self, 
                                 min_age: Optional[int] = None,
                                 max_age: Optional[int] = None,
                                 screening_type: Optional[str] = None,
                                 min_overdue_days: Optional[int] = None,
                                 max_overdue_days: Optional[int] = None,
                                 priority_level: Optional[str] = None,
                                 limit: int = 50):
        """Get overdue patients with filters"""
        args = {"limit": limit}
        
        if min_age is not None:
            args["min_age"] = min_age
        if max_age is not None:
            args["max_age"] = max_age
        if screening_type:
            args["screening_type"] = screening_type
        if min_overdue_days is not None:
            args["min_overdue_days"] = min_overdue_days
        if max_overdue_days is not None:
            args["max_overdue_days"] = max_overdue_days
        if priority_level:
            args["priority_level"] = priority_level
            
        return await self.call_tool("get_overdue_patients", args)
    
    async def get_patient_details(self, patient_id: int):
        """Get detailed information for a patient"""
        return await self.call_tool("get_patient_details", {"patient_id": patient_id})
    
    async def update_patient_record(self, patient_id: int, updates: Dict[str, Any]):
        """Update a patient record"""
        return await self.call_tool("update_patient_record", {
            "patient_id": patient_id,
            "updates": updates
        })
    
    async def close_care_gap(self, care_gap_id: int, completion_date: Optional[str] = None, notes: Optional[str] = None):
        """Close a care gap"""
        args = {"care_gap_id": care_gap_id}
        if completion_date:
            args["completion_date"] = completion_date
        if notes:
            args["notes"] = notes
            
        return await self.call_tool("close_care_gap", args)


async def test_ehr_client():
    """Test the EHR MCP client"""
    client = EHRMCPClient()
    
    try:
        # Connect to server (assuming server.py is in current directory)
        server_command = ["python", "server.py"]
        
        if not await client.connect(server_command):
            logger.error("Failed to connect to server")
            return
        
        # List available tools
        print("\n=== Available Tools ===")
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")
        
        # List available resources
        print("\n=== Available Resources ===")
        resources = await client.list_resources()
        for resource in resources:
            print(f"- {resource.name}: {resource.description}")
        
        # Test get_overdue_patients
        print("\n=== Testing get_overdue_patients ===")
        try:
            result = await client.get_overdue_patients(limit=5)
            parsed_result = json.loads(result)
            print(f"Found {parsed_result.get('total_patients', 0)} overdue patients")
            print(json.dumps(parsed_result, indent=2))
        except Exception as e:
            logger.error(f"get_overdue_patients test failed: {e}")
        
        # Test get_patient_details (using patient ID 1 if it exists)
        print("\n=== Testing get_patient_details ===")
        try:
            result = await client.get_patient_details(1)
            parsed_result = json.loads(result)
            if parsed_result.get("status") == "success":
                patient = parsed_result["patient"]
                print(f"Patient: {patient['name']} (ID: {patient['patient_id']})")
                print(f"Care Gaps: {patient['total_care_gaps']}, Open: {patient['open_care_gaps']}")
            else:
                print(f"Patient not found: {parsed_result.get('message')}")
        except Exception as e:
            logger.error(f"get_patient_details test failed: {e}")
        
        # Test update_patient_record
        print("\n=== Testing update_patient_record ===")
        try:
            updates = {
                "preferred_contact_method": "email",
                "risk_factors": "Test risk factors update via MCP"
            }
            result = await client.update_patient_record(1, updates)
            parsed_result = json.loads(result)
            print(f"Update result: {parsed_result.get('message', 'Unknown')}")
        except Exception as e:
            logger.error(f"update_patient_record test failed: {e}")
        
        print("\n=== Client Testing Complete ===")
        
    except Exception as e:
        logger.error(f"Client test failed: {e}")
    
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(test_ehr_client())