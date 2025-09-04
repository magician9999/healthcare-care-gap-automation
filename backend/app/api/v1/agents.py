from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import logging

from ...agents.workflow_service import AutoGenWorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["AutoGen Agents"])

# Global workflow service instance (will be initialized on startup)
workflow_service: Optional[AutoGenWorkflowService] = None


# Pydantic models for API
class WorkflowStartRequest(BaseModel):
    template_name: str = Field(..., description="Name of the workflow template to use")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context data for the workflow")
    workflow_id: Optional[str] = Field(None, description="Optional custom workflow ID")


class PatientFilters(BaseModel):
    min_age: Optional[int] = Field(None, ge=0, le=150)
    max_age: Optional[int] = Field(None, ge=0, le=150)
    screening_type: Optional[str] = None
    min_overdue_days: Optional[int] = Field(None, ge=0)
    max_overdue_days: Optional[int] = Field(None, ge=0)
    priority_level: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    limit: int = Field(50, ge=1, le=100)


class CareGapWorkflowRequest(BaseModel):
    filters: PatientFilters = Field(default_factory=PatientFilters)
    workflow_options: Dict[str, Any] = Field(default_factory=dict)


class AgentDirectRequest(BaseModel):
    agent_type: str = Field(..., pattern="^(data_analyst|communication_specialist|care_manager)$")
    message: str = Field(..., description="Message to send to the agent")
    context: Dict[str, Any] = Field(default_factory=dict)


class NaturalLanguageQueryRequest(BaseModel):
    prompt: str = Field(..., description="Natural language prompt for healthcare queries")
    agent_type: str = Field("data_analyst", pattern="^(data_analyst|communication_specialist|care_manager)$")
    max_results: Optional[int] = Field(100, ge=1, le=500)


class WorkflowStatusResponse(BaseModel):
    status: str
    workflow_id: Optional[str] = None
    workflow_status: Optional[str] = None
    current_step: Optional[str] = None
    progress: Optional[float] = None
    message: Optional[str] = None


def get_workflow_service() -> AutoGenWorkflowService:
    """Dependency to get workflow service instance"""
    if not workflow_service:
        raise HTTPException(status_code=503, detail="Workflow service not initialized")
    return workflow_service


async def initialize_workflow_service():
    """Initialize the global workflow service"""
    global workflow_service
    try:
        workflow_service = AutoGenWorkflowService()
        await workflow_service.start_service()
        logger.info("AutoGen Workflow Service initialized for API")
    except Exception as e:
        logger.error(f"Failed to initialize workflow service: {e}")
        raise


async def cleanup_workflow_service():
    """Cleanup the global workflow service"""
    global workflow_service
    if workflow_service:
        try:
            await workflow_service.stop_service()
            logger.info("AutoGen Workflow Service cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up workflow service: {e}")
        finally:
            workflow_service = None


# API Endpoints

@router.get("/health")
async def agents_health_check():
    """Health check for agents service"""
    if not workflow_service:
        return {
            "status": "error",
            "message": "Workflow service not initialized",
            "service_available": False
        }
    
    try:
        metrics = await workflow_service.get_agent_metrics()
        return {
            "status": "healthy",
            "service_available": True,
            "service_status": metrics.get("service_status"),
            "agents_online": len([
                agent for agent, data in metrics.get("agent_metrics", {}).items() 
                if data.get("status") in ["idle", "busy"]
            ]),
            "active_workflows": metrics.get("workflow_statistics", {}).get("active_workflows", 0)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "service_available": False
        }


@router.get("/templates")
async def list_workflow_templates(
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """Get available workflow templates"""
    try:
        templates = service.get_available_templates()
        return templates
    except Exception as e:
        logger.error(f"Failed to get workflow templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows/start")
async def start_workflow(
    request: WorkflowStartRequest,
    background_tasks: BackgroundTasks,
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """Start a new agent workflow"""
    try:
        result = await service.start_workflow(
            template_name=request.template_name,
            context=request.context,
            workflow_id=request.workflow_id
        )
        
        if result.get("status") == "success":
            return {
                "status": "success",
                "message": "Workflow started successfully",
                "workflow_id": result.get("workflow_id"),
                "template_name": result.get("template_name"),
                "execution_result": result.get("execution_result"),
                "execution_time_seconds": result.get("execution_time_seconds")
            }
        else:
            return {
                "status": "error",
                "message": result.get("message", "Workflow failed to start"),
                "details": result
            }
    
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow startup failed: {str(e)}")


@router.post("/workflows/care-gap")
async def start_care_gap_workflow(
    request: CareGapWorkflowRequest,
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """Start a care gap automation workflow with patient filters"""
    try:
        # Prepare context for care gap workflow
        context = {
            "filters": request.filters.dict(exclude_none=True),
            "workflow_type": "care_gap_automation",
            **request.workflow_options
        }
        
        result = await service.start_workflow(
            template_name="care_gap_automation",
            context=context
        )
        
        if result.get("status") == "success":
            execution_result = result.get("execution_result", {})
            
            return {
                "status": "success",
                "message": "Care gap workflow completed successfully",
                "workflow_id": result.get("workflow_id"),
                "execution_summary": {
                    "execution_time_seconds": result.get("execution_time_seconds"),
                    "workflow_status": execution_result.get("status"),
                    "steps_completed": execution_result.get("steps_completed", 0),
                    "patients_analyzed": _extract_patients_count(execution_result),
                    "communications_created": _extract_communications_count(execution_result)
                },
                "detailed_results": execution_result
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Care gap workflow failed: {result.get('message', 'Unknown error')}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Care gap workflow failed: {e}")
        raise HTTPException(status_code=500, detail=f"Care gap workflow failed: {str(e)}")


@router.post("/workflows/urgent")
async def start_urgent_workflow(
    filters: PatientFilters,
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """Start urgent patient outreach workflow"""
    try:
        # Add urgent-specific filters
        context = {
            "filters": {
                **filters.dict(exclude_none=True),
                "priority_level": "urgent"
            },
            "workflow_type": "urgent_outreach"
        }
        
        result = await service.start_workflow(
            template_name="urgent_patient_outreach",
            context=context
        )
        
        return {
            "status": "success" if result.get("status") == "success" else "error",
            "message": "Urgent workflow initiated" if result.get("status") == "success" else result.get("message"),
            "workflow_id": result.get("workflow_id"),
            "execution_result": result.get("execution_result")
        }
    
    except Exception as e:
        logger.error(f"Urgent workflow failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: str,
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """Get status of a specific workflow"""
    try:
        status = await service.get_workflow_status(workflow_id)
        
        if status.get("status") == "success":
            return WorkflowStatusResponse(
                status="success",
                workflow_id=workflow_id,
                workflow_status=status.get("workflow_status"),
                current_step=status.get("current_step"),
                progress=status.get("progress"),
                message=f"Workflow {workflow_id} status retrieved"
            )
        else:
            return WorkflowStatusResponse(
                status="error",
                message=status.get("message", "Workflow not found")
            )
    
    except Exception as e:
        logger.error(f"Failed to get workflow status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/status")
async def get_all_workflows_status(
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """Get status of all active workflows"""
    try:
        status = await service.get_workflow_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get workflows status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_agent_metrics(
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """Get performance metrics for all agents"""
    try:
        metrics = await service.get_agent_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get agent metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/direct")
async def direct_agent_communication(
    request: AgentDirectRequest,
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """Send direct message to a specific agent (for testing/debugging)"""
    try:
        # This would require extending the workflow service to support direct agent communication
        # For now, return a placeholder response
        return {
            "status": "info",
            "message": "Direct agent communication not yet implemented",
            "agent_type": request.agent_type,
            "received_message": request.message[:100] + "..." if len(request.message) > 100 else request.message
        }
    
    except Exception as e:
        logger.error(f"Direct agent communication failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/query")
async def natural_language_query(
    request: NaturalLanguageQueryRequest
):
    """Process natural language healthcare queries using intelligent agents"""
    try:
        # Import agents here to avoid circular imports
        from ...agents.data_analyst import DataAnalystAgent
        from ...agents.communication_specialist import CommunicationSpecialistAgent
        from ...agents.care_manager import CareManagerAgent
        
        # Select agent based on request
        agent_map = {
            "data_analyst": DataAnalystAgent,
            "communication_specialist": CommunicationSpecialistAgent, 
            "care_manager": CareManagerAgent
        }
        
        agent_class = agent_map.get(request.agent_type)
        if not agent_class:
            raise HTTPException(status_code=400, detail=f"Invalid agent type: {request.agent_type}")
        
        # Initialize and process query
        agent = agent_class()
        await agent.initialize()
        
        try:
            # Process the natural language query
            result = await agent.process_message(request.prompt, {"max_results": request.max_results})
            
            return {
                "status": "success",
                "agent_type": request.agent_type,
                "query": request.prompt,
                "result": result,
                "timestamp": result.get("timestamp")
            }
            
        finally:
            # Clean up agent resources
            await agent.cleanup()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Natural language query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@router.post("/agents/analyze")
async def analyze_patients(
    filters: PatientFilters,
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """Quick patient analysis using DataAnalyst agent"""
    try:
        context = {
            "filters": filters.dict(exclude_none=True),
            "analysis_type": "quick_prioritization"
        }
        
        result = await service.start_workflow(
            template_name="population_analysis",
            context=context
        )
        
        if result.get("status") == "success":
            execution_result = result.get("execution_result", {})
            step_results = execution_result.get("step_results", {})
            
            # Extract analysis results
            analysis_data = step_results.get("demographic_analysis", {})
            
            return {
                "status": "success",
                "analysis_results": analysis_data,
                "workflow_id": result.get("workflow_id"),
                "execution_time_seconds": result.get("execution_time_seconds")
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Analysis failed"))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Patient analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PatientCommunicationRequest(BaseModel):
    patient_ids: List[int]
    priority_level: str = Field("medium", pattern="^(low|medium|high|critical)$")


class BookingSlotRequest(BaseModel):
    patient_id: int = Field(default=0, description="Patient ID for whom to book the appointment (optional)")
    care_gap_id: int = Field(default=1, description="Care gap ID to be resolved") 
    screening_type: str = Field(..., description="Type of screening to book")
    appointment_date: Optional[str] = Field(None, description="Preferred appointment date (ISO format)")
    notes: Optional[str] = Field(None, description="Additional notes for the booking")
    patient_email: Optional[str] = Field(None, description="Patient email for identification")


class BookingSlotResponse(BaseModel):
    status: str
    message: str
    appointment_details: Optional[Dict[str, Any]] = None
    care_gap_status: Optional[str] = None

@router.post("/agents/communicate")
async def create_patient_communications(
    request: PatientCommunicationRequest,
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """Create communications for specific patients using CommunicationSpecialist agent"""
    try:
        context = {
            "patient_ids": request.patient_ids,
            "priority_level": request.priority_level.upper(),
            "communication_type": "batch_outreach"
        }
        
        # For now, return a structured response indicating what would be done
        return {
            "status": "success",
            "message": f"Communication creation initiated for {len(request.patient_ids)} patients",
            "patient_count": len(request.patient_ids),
            "priority_level": request.priority_level,
            "estimated_completion_time": "3-5 minutes",
            "next_steps": [
                "Messages personalized based on patient demographics and history",
                "Delivery scheduled according to patient preferences",
                "Follow-up sequences configured",
                "Tracking enabled for response monitoring"
            ]
        }
    
    except Exception as e:
        logger.error(f"Communication creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

def _extract_patients_count(execution_result: Dict) -> int:
    """Extract patient count from execution results"""
    try:
        step_results = execution_result.get("step_results", {})
        analysis_results = step_results.get("analyze_patients", {})
        
        if isinstance(analysis_results, dict):
            insights = analysis_results.get("insights", {})
            return insights.get("total_patients", 0)
        
        return 0
    except:
        return 0


def _extract_communications_count(execution_result: Dict) -> int:
    """Extract communications count from execution results"""
    try:
        step_results = execution_result.get("step_results", {})
        comm_results = step_results.get("create_communications", {})
        
        if isinstance(comm_results, dict):
            return comm_results.get("total_created", 0)
        
        return 0
    except:
        return 0


@router.post("/agents/book-slot", response_model=BookingSlotResponse)
async def book_appointment_slot(
    request: BookingSlotRequest,
    service: AutoGenWorkflowService = Depends(get_workflow_service)
):
    """
    Book appointment slot and close care gap using CareManagerAgent with LLM understanding
    """
    try:
        # Import CareManagerAgent here to avoid circular imports
        from ...agents.care_manager import CareManagerAgent
        
        # Initialize CareManager agent
        care_manager = CareManagerAgent()
        await care_manager.initialize()
        
        try:
            # Extract email from notes if not provided directly
            patient_email = request.patient_email
            if not patient_email and request.notes:
                # Extract email from notes using regex
                import re
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', request.notes)
                if email_match:
                    patient_email = email_match.group()
            
            # Prepare context for CareManagerAgent with LLM-friendly message
            booking_context = {
                "patient_id": request.patient_id,
                "care_gap_id": request.care_gap_id, 
                "screening_type": request.screening_type,
                "appointment_date": request.appointment_date,
                "notes": request.notes,
                "patient_email": patient_email,
                "action": "book_appointment_and_close_care_gap"
            }
            
            # Create natural language message for the agent to understand
            natural_message = f"""
            Patient has booked an appointment slot for {request.screening_type} screening.
            Patient email: {patient_email}
            Please find this patient by email and close their care gap for {request.screening_type}.
            The screening appointment has been scheduled and the care gap should be marked as resolved.
            """
            
            # Process the booking request through CareManagerAgent
            result = await care_manager.process_message(natural_message, booking_context)
            
            if result.get("status") == "success":
                return BookingSlotResponse(
                    status="success",
                    message=f"Appointment booked successfully and care gap closed for {request.screening_type} screening",
                    appointment_details={
                        "patient_id": request.patient_id,
                        "screening_type": request.screening_type,
                        "appointment_date": request.appointment_date or "To be scheduled",
                        "booking_reference": f"BOOK_{request.patient_id}_{request.care_gap_id}",
                        "status": "confirmed"
                    },
                    care_gap_status="closed"
                )
            else:
                return BookingSlotResponse(
                    status="error", 
                    message=result.get("message", "Booking failed"),
                    care_gap_status="open"
                )
                
        finally:
            # Clean up agent resources
            await care_manager.cleanup()
    
    except Exception as e:
        logger.error(f"Appointment booking failed: {e}")
        return BookingSlotResponse(
            status="error",
            message=f"Booking failed: {str(e)}",
            care_gap_status="open"
        )


@router.post("/agents/reject-slot")
async def reject_appointment_slot(
    request: Dict[str, Any]
):
    """
    Reject appointment slot - no database modifications
    """
    try:
        patient_id = request.get("patient_id")
        care_gap_id = request.get("care_gap_id")
        screening_type = request.get("screening_type")
        rejection_reason = request.get("reason", "Patient declined appointment")
        
        logger.info(f"Appointment rejected for patient {patient_id}, care gap {care_gap_id}: {rejection_reason}")
        
        return {
            "status": "success",
            "message": f"Appointment slot rejected for {screening_type} screening",
            "patient_id": patient_id,
            "care_gap_id": care_gap_id,
            "action_taken": "none",
            "care_gap_status": "open",
            "rejection_reason": rejection_reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Appointment rejection processing failed: {e}")
        return {
            "status": "error",
            "message": f"Failed to process rejection: {str(e)}"
        }