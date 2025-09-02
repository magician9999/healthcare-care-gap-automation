import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor
import traceback

from .data_analyst import DataAnalystAgent
from .communication_specialist import CommunicationSpecialistAgent
from .care_manager import CareManagerAgent

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    DATA_ANALYST = "data_analyst"
    COMMUNICATION_SPECIALIST = "communication_specialist"
    CARE_MANAGER = "care_manager"


class WorkflowPattern(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel" 
    PIPELINE = "pipeline"
    CONDITIONAL = "conditional"


class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_activity: Optional[datetime] = None
    uptime_start: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0.0
    
    @property  
    def error_rate(self) -> float:
        return (self.failed_requests / self.total_requests * 100) if self.total_requests > 0 else 0.0


@dataclass
class WorkflowState:
    """Workflow execution state"""
    workflow_id: str
    pattern: WorkflowPattern
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    progress: float = 0.0
    results: Dict[str, Any] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = {}
        if self.errors is None:
            self.errors = []


class AutoGenWorkflowService:
    """
    Central service for managing AutoGen multi-agent healthcare workflows
    Handles agent lifecycle, communication, state management, and monitoring
    """
    
    def __init__(self):
        # Agent management
        self.agents: Dict[AgentRole, Any] = {}
        self.agent_status: Dict[AgentRole, AgentStatus] = {}
        self.agent_metrics: Dict[AgentRole, AgentMetrics] = {}
        self.agent_locks: Dict[AgentRole, threading.Lock] = {}
        
        # Workflow management
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.workflow_history: List[WorkflowState] = []
        self.workflow_templates: Dict[str, Dict] = {}
        
        # Service configuration
        self.max_concurrent_workflows = 5
        self.agent_timeout = 300  # 5 minutes
        self.workflow_timeout = 1800  # 30 minutes
        self.cleanup_interval = 3600  # 1 hour
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="autogen_workflow")
        
        # Service state
        self.service_started = False
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Initialize workflow templates
        self._initialize_workflow_templates()
        
        logger.info("AutoGen Workflow Service initialized")
    
    async def start_service(self):
        """Start the workflow service and initialize agents"""
        if self.service_started:
            logger.warning("Workflow service already started")
            return
        
        try:
            logger.info("Starting AutoGen Workflow Service...")
            
            # Initialize agents
            await self._initialize_agents()
            
            # Start background cleanup task
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
            
            self.service_started = True
            logger.info("AutoGen Workflow Service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start workflow service: {e}")
            raise
    
    async def stop_service(self):
        """Stop the workflow service and cleanup resources"""
        if not self.service_started:
            return
        
        logger.info("Stopping AutoGen Workflow Service...")
        
        try:
            # Cancel cleanup task
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel active workflows
            for workflow_id in list(self.active_workflows.keys()):
                await self._cancel_workflow(workflow_id, "Service shutdown")
            
            # Cleanup agents
            await self._cleanup_agents()
            
            # Shutdown thread pool
            self.executor.shutdown(wait=True)
            
            self.service_started = False
            logger.info("AutoGen Workflow Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping workflow service: {e}")
    
    async def _initialize_agents(self):
        """Initialize all healthcare agents"""
        try:
            # Initialize Data Analyst Agent
            self.agents[AgentRole.DATA_ANALYST] = DataAnalystAgent()
            await self.agents[AgentRole.DATA_ANALYST].initialize()
            self.agent_status[AgentRole.DATA_ANALYST] = AgentStatus.IDLE
            self.agent_metrics[AgentRole.DATA_ANALYST] = AgentMetrics(uptime_start=datetime.utcnow())
            self.agent_locks[AgentRole.DATA_ANALYST] = threading.Lock()
            
            # Initialize Communication Specialist Agent
            self.agents[AgentRole.COMMUNICATION_SPECIALIST] = CommunicationSpecialistAgent()
            await self.agents[AgentRole.COMMUNICATION_SPECIALIST].initialize()
            self.agent_status[AgentRole.COMMUNICATION_SPECIALIST] = AgentStatus.IDLE
            self.agent_metrics[AgentRole.COMMUNICATION_SPECIALIST] = AgentMetrics(uptime_start=datetime.utcnow())
            self.agent_locks[AgentRole.COMMUNICATION_SPECIALIST] = threading.Lock()
            
            # Initialize Care Manager Agent
            self.agents[AgentRole.CARE_MANAGER] = CareManagerAgent()
            await self.agents[AgentRole.CARE_MANAGER].initialize()
            self.agent_status[AgentRole.CARE_MANAGER] = AgentStatus.IDLE
            self.agent_metrics[AgentRole.CARE_MANAGER] = AgentMetrics(uptime_start=datetime.utcnow())
            self.agent_locks[AgentRole.CARE_MANAGER] = threading.Lock()
            
            logger.info("All healthcare agents initialized successfully")
            
        except Exception as e:
            logger.error(f"Agent initialization failed: {e}")
            # Cleanup any successfully initialized agents
            await self._cleanup_agents()
            raise
    
    async def _cleanup_agents(self):
        """Cleanup all agents"""
        for role, agent in self.agents.items():
            try:
                if hasattr(agent, 'cleanup'):
                    await agent.cleanup()
                self.agent_status[role] = AgentStatus.OFFLINE
            except Exception as e:
                logger.error(f"Error cleaning up agent {role}: {e}")
        
        self.agents.clear()
        self.agent_status.clear()
        self.agent_metrics.clear()
        self.agent_locks.clear()
    
    def _initialize_workflow_templates(self):
        """Initialize predefined workflow templates"""
        
        # Standard care gap automation workflow
        self.workflow_templates["care_gap_automation"] = {
            "name": "Care Gap Automation",
            "description": "End-to-end care gap identification, prioritization, and patient outreach",
            "pattern": WorkflowPattern.SEQUENTIAL,
            "steps": [
                {
                    "step_id": "analyze_patients",
                    "agent": AgentRole.DATA_ANALYST,
                    "message": "prioritize overdue patients",
                    "timeout": 300,
                    "required_context": ["filters"]
                },
                {
                    "step_id": "create_communications", 
                    "agent": AgentRole.COMMUNICATION_SPECIALIST,
                    "message": "create outreach message",
                    "timeout": 180,
                    "required_context": ["prioritized_patients"]
                },
                {
                    "step_id": "orchestrate_workflow",
                    "agent": AgentRole.CARE_MANAGER,
                    "message": "start workflow",
                    "timeout": 600,
                    "required_context": ["analysis_results", "communication_results"]
                }
            ],
            "error_handling": {
                "retry_count": 2,
                "fallback_strategy": "partial_completion"
            }
        }
        
        # High-priority patient workflow
        self.workflow_templates["urgent_patient_outreach"] = {
            "name": "Urgent Patient Outreach",
            "description": "Fast-track workflow for high-priority patients",
            "pattern": WorkflowPattern.PIPELINE,
            "steps": [
                {
                    "step_id": "identify_urgent",
                    "agent": AgentRole.DATA_ANALYST,
                    "message": "risk assessment",
                    "timeout": 120
                },
                {
                    "step_id": "urgent_communication",
                    "agent": AgentRole.COMMUNICATION_SPECIALIST,
                    "message": "create outreach message",
                    "timeout": 60
                },
                {
                    "step_id": "immediate_action",
                    "agent": AgentRole.CARE_MANAGER,
                    "message": "handle exception",
                    "timeout": 180
                }
            ]
        }
        
        # Analytics-focused workflow
        self.workflow_templates["population_analysis"] = {
            "name": "Population Health Analysis",
            "description": "Comprehensive analysis of patient population care gaps",
            "pattern": WorkflowPattern.PARALLEL,
            "steps": [
                {
                    "step_id": "demographic_analysis",
                    "agent": AgentRole.DATA_ANALYST,
                    "message": "analyze patient cohort",
                    "timeout": 600
                },
                {
                    "step_id": "communication_strategy",
                    "agent": AgentRole.COMMUNICATION_SPECIALIST, 
                    "message": "batch communications",
                    "timeout": 300
                }
            ]
        }
        
        logger.info(f"Initialized {len(self.workflow_templates)} workflow templates")
    
    async def start_workflow(self, template_name: str, context: Dict[str, Any], 
                           workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Start a new workflow based on a template"""
        
        if not self.service_started:
            raise RuntimeError("Workflow service not started")
        
        if len(self.active_workflows) >= self.max_concurrent_workflows:
            return {
                "status": "error",
                "message": f"Maximum concurrent workflows ({self.max_concurrent_workflows}) reached",
                "active_workflows": len(self.active_workflows)
            }
        
        if template_name not in self.workflow_templates:
            return {
                "status": "error",
                "message": f"Workflow template '{template_name}' not found",
                "available_templates": list(self.workflow_templates.keys())
            }
        
        # Generate workflow ID if not provided
        if not workflow_id:
            workflow_id = f"{template_name}_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"
        
        template = self.workflow_templates[template_name]
        
        # Create workflow state
        workflow_state = WorkflowState(
            workflow_id=workflow_id,
            pattern=template["pattern"],
            status="initializing",
            created_at=datetime.utcnow()
        )
        
        self.active_workflows[workflow_id] = workflow_state
        
        try:
            logger.info(f"Starting workflow '{template_name}' with ID: {workflow_id}")
            
            # Execute workflow based on pattern
            if template["pattern"] == WorkflowPattern.SEQUENTIAL:
                result = await self._execute_sequential_workflow(workflow_id, template, context)
            elif template["pattern"] == WorkflowPattern.PARALLEL:
                result = await self._execute_parallel_workflow(workflow_id, template, context)
            elif template["pattern"] == WorkflowPattern.PIPELINE:
                result = await self._execute_pipeline_workflow(workflow_id, template, context)
            else:
                result = {"status": "error", "message": f"Unsupported workflow pattern: {template['pattern']}"}
            
            # Update workflow state
            workflow_state.status = "completed" if result.get("status") == "success" else "failed"
            workflow_state.completed_at = datetime.utcnow()
            workflow_state.results = result
            workflow_state.progress = 100.0
            
            # Move to history
            self.workflow_history.append(workflow_state)
            del self.active_workflows[workflow_id]
            
            logger.info(f"Workflow {workflow_id} completed with status: {workflow_state.status}")
            
            return {
                "status": "success",
                "workflow_id": workflow_id,
                "template_name": template_name,
                "execution_result": result,
                "execution_time_seconds": (workflow_state.completed_at - workflow_state.created_at).total_seconds()
            }
            
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            traceback.print_exc()
            
            workflow_state.status = "failed"
            workflow_state.completed_at = datetime.utcnow()
            workflow_state.errors.append(str(e))
            
            # Move to history
            self.workflow_history.append(workflow_state)
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
            
            return {
                "status": "error",
                "workflow_id": workflow_id,
                "message": f"Workflow execution failed: {str(e)}",
                "error_details": traceback.format_exc()
            }
    
    async def _execute_sequential_workflow(self, workflow_id: str, template: Dict, context: Dict) -> Dict[str, Any]:
        """Execute workflow steps sequentially"""
        
        workflow_state = self.active_workflows[workflow_id]
        workflow_state.status = "running"
        workflow_state.started_at = datetime.utcnow()
        
        results = {}
        step_count = len(template["steps"])
        
        for i, step in enumerate(template["steps"]):
            try:
                workflow_state.current_step = step["step_id"]
                workflow_state.progress = (i / step_count) * 100
                
                logger.info(f"Executing step {i+1}/{step_count}: {step['step_id']}")
                
                # Prepare step context
                step_context = {**context}
                
                # Add results from previous steps
                if "required_context" in step:
                    for req_key in step["required_context"]:
                        if req_key in results:
                            step_context[req_key] = results[req_key]
                        elif req_key not in context:
                            logger.warning(f"Required context '{req_key}' not available for step {step['step_id']}")
                
                # Execute step
                step_result = await self._execute_agent_step(
                    step["agent"],
                    step["message"],
                    step_context,
                    step.get("timeout", self.agent_timeout)
                )
                
                if step_result.get("status") != "success":
                    # Handle step failure
                    error_msg = f"Step {step['step_id']} failed: {step_result.get('message', 'Unknown error')}"
                    workflow_state.errors.append(error_msg)
                    
                    # Check if we should retry or fail
                    retry_count = template.get("error_handling", {}).get("retry_count", 0)
                    if retry_count > 0:
                        logger.info(f"Retrying step {step['step_id']} (attempts remaining: {retry_count})")
                        # TODO: Implement retry logic
                    
                    # For now, fail the workflow
                    raise Exception(error_msg)
                
                results[step["step_id"]] = step_result.get("data", step_result)
                logger.info(f"Step {step['step_id']} completed successfully")
                
            except Exception as e:
                logger.error(f"Step {step['step_id']} execution failed: {e}")
                workflow_state.errors.append(str(e))
                raise
        
        return {
            "status": "success",
            "workflow_pattern": "sequential",
            "steps_completed": step_count,
            "step_results": results,
            "execution_summary": "All steps completed successfully"
        }
    
    async def _execute_parallel_workflow(self, workflow_id: str, template: Dict, context: Dict) -> Dict[str, Any]:
        """Execute workflow steps in parallel"""
        
        workflow_state = self.active_workflows[workflow_id]
        workflow_state.status = "running"
        workflow_state.started_at = datetime.utcnow()
        
        # Create tasks for all steps
        tasks = []
        step_names = []
        
        for step in template["steps"]:
            step_context = {**context}
            
            task = self._execute_agent_step(
                step["agent"],
                step["message"],
                step_context,
                step.get("timeout", self.agent_timeout)
            )
            
            tasks.append(task)
            step_names.append(step["step_id"])
        
        # Execute all tasks in parallel
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            step_results = {}
            successful_steps = 0
            failed_steps = 0
            
            for i, (step_name, result) in enumerate(zip(step_names, results)):
                if isinstance(result, Exception):
                    workflow_state.errors.append(f"Step {step_name} failed: {str(result)}")
                    step_results[step_name] = {"status": "error", "message": str(result)}
                    failed_steps += 1
                elif result.get("status") == "success":
                    step_results[step_name] = result
                    successful_steps += 1
                else:
                    workflow_state.errors.append(f"Step {step_name} failed: {result.get('message', 'Unknown error')}")
                    step_results[step_name] = result
                    failed_steps += 1
            
            # Determine overall success
            if failed_steps == 0:
                status = "success"
                summary = f"All {successful_steps} steps completed successfully"
            elif successful_steps > 0:
                status = "partial_success"
                summary = f"{successful_steps} steps succeeded, {failed_steps} failed"
            else:
                status = "error"
                summary = f"All {failed_steps} steps failed"
            
            return {
                "status": status,
                "workflow_pattern": "parallel",
                "steps_completed": successful_steps,
                "steps_failed": failed_steps,
                "step_results": step_results,
                "execution_summary": summary
            }
            
        except Exception as e:
            logger.error(f"Parallel workflow execution failed: {e}")
            workflow_state.errors.append(str(e))
            raise
    
    async def _execute_pipeline_workflow(self, workflow_id: str, template: Dict, context: Dict) -> Dict[str, Any]:
        """Execute workflow as a pipeline with data flowing between steps"""
        
        # For now, implement as sequential with better data flow
        # In a full implementation, this would handle streaming data between agents
        return await self._execute_sequential_workflow(workflow_id, template, context)
    
    async def _execute_agent_step(self, agent_role: AgentRole, message: str, 
                                context: Dict, timeout: int) -> Dict[str, Any]:
        """Execute a single agent step with metrics and error handling"""
        
        if agent_role not in self.agents:
            raise ValueError(f"Agent {agent_role} not initialized")
        
        agent = self.agents[agent_role]
        metrics = self.agent_metrics[agent_role]
        
        # Update agent status
        self.agent_status[agent_role] = AgentStatus.BUSY
        start_time = datetime.utcnow()
        
        try:
            # Execute agent with timeout
            result = await asyncio.wait_for(
                agent.process_message(message, context),
                timeout=timeout
            )
            
            # Update metrics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            metrics.total_requests += 1
            metrics.successful_requests += 1
            metrics.last_activity = datetime.utcnow()
            metrics.average_response_time = (
                (metrics.average_response_time * (metrics.total_requests - 1) + execution_time) 
                / metrics.total_requests
            )
            
            self.agent_status[agent_role] = AgentStatus.IDLE
            
            return result
            
        except asyncio.TimeoutError:
            metrics.total_requests += 1
            metrics.failed_requests += 1
            metrics.last_activity = datetime.utcnow()
            self.agent_status[agent_role] = AgentStatus.ERROR
            
            raise Exception(f"Agent {agent_role} timed out after {timeout} seconds")
            
        except Exception as e:
            metrics.total_requests += 1
            metrics.failed_requests += 1
            metrics.last_activity = datetime.utcnow()
            self.agent_status[agent_role] = AgentStatus.ERROR
            
            raise Exception(f"Agent {agent_role} execution failed: {str(e)}")
    
    async def get_workflow_status(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of specific workflow or all active workflows"""
        
        if workflow_id:
            # Get specific workflow status
            if workflow_id in self.active_workflows:
                workflow_state = self.active_workflows[workflow_id]
                return {
                    "status": "success",
                    "workflow_id": workflow_id,
                    "workflow_status": workflow_state.status,
                    "current_step": workflow_state.current_step,
                    "progress": workflow_state.progress,
                    "started_at": workflow_state.started_at.isoformat() if workflow_state.started_at else None,
                    "errors": workflow_state.errors
                }
            else:
                # Check workflow history
                historical_workflow = next(
                    (wf for wf in self.workflow_history if wf.workflow_id == workflow_id),
                    None
                )
                
                if historical_workflow:
                    return {
                        "status": "success",
                        "workflow_id": workflow_id,
                        "workflow_status": historical_workflow.status,
                        "completed_at": historical_workflow.completed_at.isoformat() if historical_workflow.completed_at else None,
                        "execution_time_seconds": (
                            (historical_workflow.completed_at - historical_workflow.created_at).total_seconds()
                            if historical_workflow.completed_at else None
                        ),
                        "results": historical_workflow.results
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Workflow {workflow_id} not found"
                    }
        else:
            # Get all active workflows status
            active_workflows = []
            
            for wf_id, wf_state in self.active_workflows.items():
                active_workflows.append({
                    "workflow_id": wf_id,
                    "status": wf_state.status,
                    "progress": wf_state.progress,
                    "current_step": wf_state.current_step,
                    "created_at": wf_state.created_at.isoformat(),
                    "error_count": len(wf_state.errors)
                })
            
            return {
                "status": "success",
                "active_workflows": active_workflows,
                "total_active": len(active_workflows),
                "total_historical": len(self.workflow_history),
                "service_uptime": (datetime.utcnow() - min(
                    metrics.uptime_start for metrics in self.agent_metrics.values()
                )).total_seconds() if self.agent_metrics else 0
            }
    
    async def get_agent_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all agents"""
        
        agent_metrics = {}
        
        for role, metrics in self.agent_metrics.items():
            agent_metrics[role.value] = {
                "status": self.agent_status[role].value,
                "total_requests": metrics.total_requests,
                "successful_requests": metrics.successful_requests,
                "failed_requests": metrics.failed_requests,
                "success_rate": round(metrics.success_rate, 2),
                "error_rate": round(metrics.error_rate, 2),
                "average_response_time": round(metrics.average_response_time, 3),
                "last_activity": metrics.last_activity.isoformat() if metrics.last_activity else None,
                "uptime_hours": (datetime.utcnow() - metrics.uptime_start).total_seconds() / 3600 if metrics.uptime_start else 0
            }
        
        return {
            "status": "success",
            "service_status": "running" if self.service_started else "stopped",
            "agent_metrics": agent_metrics,
            "workflow_statistics": {
                "active_workflows": len(self.active_workflows),
                "completed_workflows": len([wf for wf in self.workflow_history if wf.status == "completed"]),
                "failed_workflows": len([wf for wf in self.workflow_history if wf.status == "failed"]),
                "total_workflows": len(self.workflow_history)
            }
        }
    
    async def _cancel_workflow(self, workflow_id: str, reason: str):
        """Cancel an active workflow"""
        
        if workflow_id in self.active_workflows:
            workflow_state = self.active_workflows[workflow_id]
            workflow_state.status = "cancelled"
            workflow_state.completed_at = datetime.utcnow()
            workflow_state.errors.append(f"Cancelled: {reason}")
            
            # Move to history
            self.workflow_history.append(workflow_state)
            del self.active_workflows[workflow_id]
            
            logger.info(f"Workflow {workflow_id} cancelled: {reason}")
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old workflow data and metrics reset"""
        
        while self.service_started:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self.service_started:
                    break
                
                # Cleanup old workflow history (keep last 100)
                if len(self.workflow_history) > 100:
                    self.workflow_history = self.workflow_history[-100:]
                
                # Reset agent status if they've been in error state for too long
                current_time = datetime.utcnow()
                
                for role, status in self.agent_status.items():
                    if status == AgentStatus.ERROR:
                        metrics = self.agent_metrics[role]
                        if metrics.last_activity and (current_time - metrics.last_activity).total_seconds() > 600:  # 10 minutes
                            self.agent_status[role] = AgentStatus.IDLE
                            logger.info(f"Reset agent {role} status from ERROR to IDLE after timeout")
                
                logger.info("Periodic cleanup completed")
                
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
    
    def get_available_templates(self) -> Dict[str, Any]:
        """Get list of available workflow templates"""
        
        templates_info = {}
        
        for name, template in self.workflow_templates.items():
            templates_info[name] = {
                "name": template["name"],
                "description": template["description"],
                "pattern": template["pattern"].value,
                "step_count": len(template["steps"]),
                "agents_involved": list(set(step["agent"].value for step in template["steps"]))
            }
        
        return {
            "status": "success",
            "available_templates": templates_info,
            "total_templates": len(templates_info)
        }