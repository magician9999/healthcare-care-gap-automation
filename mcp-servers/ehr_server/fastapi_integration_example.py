#!/usr/bin/env python3

"""
FastAPI Integration Example for EHR MCP Server

This example shows how to integrate the EHR MCP server with FastAPI endpoints
to create a unified API that leverages MCP tools for EHR operations.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from client import EHRMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Healthcare EHR API",
    description="FastAPI integration with EHR MCP Server",
    version="1.0.0"
)

# Global MCP client
mcp_client = None


# Pydantic models for API
class PatientFilter(BaseModel):
    min_age: Optional[int] = Field(None, ge=0, le=150)
    max_age: Optional[int] = Field(None, ge=0, le=150)
    screening_type: Optional[str] = None
    min_overdue_days: Optional[int] = Field(None, ge=0)
    max_overdue_days: Optional[int] = Field(None, ge=0)
    priority_level: Optional[str] = Field(None, regex="^(low|medium|high|urgent)$")
    limit: int = Field(50, ge=1, le=100)


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=150)
    email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$')
    phone: Optional[str] = None
    insurance_info: Optional[Dict[str, Any]] = None
    risk_factors: Optional[str] = None
    preferred_contact_method: Optional[str] = Field(None, regex="^(email|phone|sms|mail)$")


class CareGapClosure(BaseModel):
    completion_date: Optional[str] = Field(None, regex=r'^\d{4}-\d{2}-\d{2}$')
    notes: Optional[str] = None


# Dependency to get MCP client
async def get_mcp_client() -> EHRMCPClient:
    """Get or create MCP client connection"""
    global mcp_client
    
    if mcp_client is None:
        mcp_client = EHRMCPClient()
        server_command = ["python", "mcp-servers/ehr_server/server.py"]
        
        connected = await mcp_client.connect(server_command)
        if not connected:
            raise HTTPException(status_code=503, detail="EHR MCP server unavailable")
    
    return mcp_client


# API Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Healthcare EHR API",
        "mcp_server": "connected" if mcp_client else "not_connected"
    }


@app.get("/patients/overdue")
async def get_overdue_patients(
    filters: PatientFilter = Depends(),
    client: EHRMCPClient = Depends(get_mcp_client)
):
    """Get patients with overdue care gap screenings"""
    try:
        # Convert Pydantic model to dict, excluding None values
        filter_dict = {k: v for k, v in filters.dict().items() if v is not None}
        
        result = await client.get_overdue_patients(**filter_dict)
        parsed_result = json.loads(result)
        
        if parsed_result.get("status") != "success":
            raise HTTPException(
                status_code=400,
                detail=parsed_result.get("message", "Failed to retrieve overdue patients")
            )
        
        return parsed_result
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid response from EHR server")
    except Exception as e:
        logger.error(f"Error getting overdue patients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/patients/{patient_id}")
async def get_patient_details(
    patient_id: int,
    client: EHRMCPClient = Depends(get_mcp_client)
):
    """Get detailed information for a specific patient"""
    try:
        result = await client.get_patient_details(patient_id)
        parsed_result = json.loads(result)
        
        if parsed_result.get("status") == "error":
            if "not found" in parsed_result.get("message", "").lower():
                raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
            else:
                raise HTTPException(status_code=400, detail=parsed_result.get("message"))
        
        return parsed_result
        
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid response from EHR server")
    except Exception as e:
        logger.error(f"Error getting patient details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/patients/{patient_id}")
async def update_patient(
    patient_id: int,
    updates: PatientUpdate,
    client: EHRMCPClient = Depends(get_mcp_client)
):
    """Update patient record information"""
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid updates provided")
        
        result = await client.update_patient_record(patient_id, update_dict)
        parsed_result = json.loads(result)
        
        if parsed_result.get("status") == "error":
            if "not found" in parsed_result.get("message", "").lower():
                raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
            else:
                raise HTTPException(status_code=400, detail=parsed_result.get("message"))
        
        return parsed_result
        
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid response from EHR server")
    except Exception as e:
        logger.error(f"Error updating patient: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/care-gaps/{care_gap_id}/close")
async def close_care_gap(
    care_gap_id: int,
    closure: CareGapClosure = CareGapClosure(),
    client: EHRMCPClient = Depends(get_mcp_client)
):
    """Mark a care gap as closed/completed"""
    try:
        result = await client.close_care_gap(
            care_gap_id,
            closure.completion_date,
            closure.notes
        )
        parsed_result = json.loads(result)
        
        if parsed_result.get("status") == "error":
            if "not found" in parsed_result.get("message", "").lower():
                raise HTTPException(status_code=404, detail=f"Care gap {care_gap_id} not found")
            else:
                raise HTTPException(status_code=400, detail=parsed_result.get("message"))
        
        return parsed_result
        
    except HTTPException:
        raise
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid response from EHR server")
    except Exception as e:
        logger.error(f"Error closing care gap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/tools")
async def list_mcp_tools(client: EHRMCPClient = Depends(get_mcp_client)):
    """List available MCP tools"""
    try:
        tools = await client.list_tools()
        return {
            "status": "success",
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description
                }
                for tool in tools
            ]
        }
    except Exception as e:
        logger.error(f"Error listing MCP tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/resources")
async def list_mcp_resources(client: EHRMCPClient = Depends(get_mcp_client)):
    """List available MCP resources"""
    try:
        resources = await client.list_resources()
        return {
            "status": "success", 
            "resources": [
                {
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": resource.description
                }
                for resource in resources
            ]
        }
    except Exception as e:
        logger.error(f"Error listing MCP resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize MCP client on startup"""
    logger.info("Starting Healthcare EHR API...")
    # MCP client will be initialized on first use


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up MCP client on shutdown"""
    global mcp_client
    if mcp_client:
        await mcp_client.disconnect()
        mcp_client = None
    logger.info("Healthcare EHR API shutdown complete")


# Example usage and testing
if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting FastAPI with EHR MCP integration...")
    uvicorn.run(
        "fastapi_integration_example:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )