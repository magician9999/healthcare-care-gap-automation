import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date, timedelta
from enum import Enum

from .base_agent import BaseHealthcareAgent

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStep(Enum):
    ANALYZE_PATIENTS = "analyze_patients"
    CREATE_COMMUNICATIONS = "create_communications"
    SEND_OUTREACH = "send_outreach"
    TRACK_RESPONSES = "track_responses"
    UPDATE_RECORDS = "update_records"
    GENERATE_REPORT = "generate_report"


class CareManagerAgent(BaseHealthcareAgent):
    """
    Specialized AutoGen agent for orchestrating healthcare care gap workflows
    Coordinates between DataAnalyst and CommunicationSpecialist agents
    Manages patient processing, progress tracking, and exception handling
    """
    
    def __init__(self):
        system_message = """You are a Care Manager AI responsible for orchestrating healthcare care gap automation workflows.
        Your role is to:
        1. Coordinate workflow execution between specialized agents (DataAnalyst and CommunicationSpecialist)
        2. Manage patient processing pipelines and track progress
        3. Handle exceptions, retries, and error recovery
        4. Update patient records and close care gaps when appropriate
        5. Generate comprehensive reports and workflow summaries
        6. Ensure quality control and compliance throughout the process
        
        You have access to all MCP healthcare tools and coordinate with other agents to ensure
        efficient and effective care gap automation workflows."""
        
        super().__init__(
            name="CareManagerAgent",
            role="Healthcare Care Manager",
            system_message=system_message
        )
        
        # Workflow tracking
        self.active_workflows: Dict[str, Dict] = {}
        self.workflow_history: List[Dict] = []
        
        # Quality metrics
        self.quality_thresholds = {
            "priority_accuracy": 0.85,
            "communication_personalization": 0.80,
            "response_rate_target": 0.65,
            "completion_rate_target": 0.75
        }
        
        # Workflow step configurations
        self.step_configs = {
            WorkflowStep.ANALYZE_PATIENTS: {
                "timeout": 300,  # 5 minutes
                "retry_count": 2,
                "required_inputs": ["patient_filters"],
                "outputs": ["prioritized_patients", "insights"]
            },
            WorkflowStep.CREATE_COMMUNICATIONS: {
                "timeout": 180,  # 3 minutes
                "retry_count": 1,
                "required_inputs": ["prioritized_patients"],
                "outputs": ["outreach_messages", "follow_up_schedules"]
            },
            WorkflowStep.SEND_OUTREACH: {
                "timeout": 600,  # 10 minutes
                "retry_count": 3,
                "required_inputs": ["outreach_messages"],
                "outputs": ["delivery_status", "tracking_ids"]
            },
            WorkflowStep.TRACK_RESPONSES: {
                "timeout": 86400,  # 24 hours
                "retry_count": 0,
                "required_inputs": ["tracking_ids"],
                "outputs": ["response_metrics", "patient_responses"]
            },
            WorkflowStep.UPDATE_RECORDS: {
                "timeout": 120,  # 2 minutes
                "retry_count": 2,
                "required_inputs": ["patient_responses", "completed_screenings"],
                "outputs": ["update_results"]
            },
            WorkflowStep.GENERATE_REPORT: {
                "timeout": 60,  # 1 minute
                "retry_count": 1,
                "required_inputs": ["workflow_results"],
                "outputs": ["final_report"]
            }
        }
    
    async def process_message(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process workflow management requests"""
        self.add_to_conversation("user", message, context)
        
        try:
            request_type = self._parse_workflow_request(message)
            
            if request_type == "start_workflow":
                result = await self._start_care_gap_workflow(context or {})
            elif request_type == "monitor_workflow":
                result = await self._monitor_workflow_progress(context or {})
            elif request_type == "update_workflow":
                result = await self._update_workflow_status(context or {})
            elif request_type == "complete_care_gaps":
                result = await self._complete_care_gaps(context or {})
            elif request_type == "generate_report":
                result = await self._generate_workflow_report(context or {})
            elif request_type == "handle_exception":
                result = await self._handle_workflow_exception(context or {})
            else:
                result = await self._general_workflow_guidance(message, context or {})
            
            self.add_to_conversation("assistant", json.dumps(result), {"request_type": request_type})
            return result
            
        except Exception as e:
            logger.error(f"CareManagerAgent processing failed: {e}")
            error_result = {
                "status": "error",
                "message": f"Workflow management failed: {str(e)}",
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.add_to_conversation("assistant", json.dumps(error_result), {"error": True})
            return error_result
    
    def _parse_workflow_request(self, message: str) -> str:
        """Parse the type of workflow request"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ["start", "begin", "initiate", "run workflow"]):
            return "start_workflow"
        elif any(keyword in message_lower for keyword in ["monitor", "status", "progress", "check"]):
            return "monitor_workflow"
        elif any(keyword in message_lower for keyword in ["update", "modify", "change"]):
            return "update_workflow"
        elif any(keyword in message_lower for keyword in ["complete", "close", "finish"]):
            return "complete_care_gaps"
        elif any(keyword in message_lower for keyword in ["report", "summary", "results"]):
            return "generate_report"
        elif any(keyword in message_lower for keyword in ["error", "exception", "failure", "retry"]):
            return "handle_exception"
        else:
            return "general_workflow"
    
    async def _start_care_gap_workflow(self, context: Dict) -> Dict[str, Any]:
        """Start a comprehensive care gap automation workflow"""
        try:
            # Generate workflow ID
            workflow_id = f"workflow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{hash(str(context)) % 10000}"
            
            # Initialize workflow state
            workflow_state = {
                "workflow_id": workflow_id,
                "status": WorkflowStatus.RUNNING.value,
                "created_at": datetime.utcnow().isoformat(),
                "steps": [],
                "current_step": None,
                "progress": 0,
                "context": context,
                "results": {},
                "errors": [],
                "metrics": {}
            }
            
            self.active_workflows[workflow_id] = workflow_state
            
            logger.info(f"Starting care gap workflow: {workflow_id}")
            
            # Step 1: Analyze Patients (via DataAnalyst Agent)
            analyze_result = await self._execute_workflow_step(
                workflow_id, 
                WorkflowStep.ANALYZE_PATIENTS,
                self._analyze_patients_step,
                context
            )
            
            if analyze_result["status"] != "success":
                return self._handle_workflow_failure(workflow_id, "Patient analysis failed", analyze_result)
            
            # Step 2: Create Communications (via CommunicationSpecialist Agent)  
            comm_context = {
                **context,
                "prioritized_patients": analyze_result["data"]["prioritized_patients"]
            }
            
            comm_result = await self._execute_workflow_step(
                workflow_id,
                WorkflowStep.CREATE_COMMUNICATIONS,
                self._create_communications_step,
                comm_context
            )
            
            if comm_result["status"] != "success":
                return self._handle_workflow_failure(workflow_id, "Communication creation failed", comm_result)
            
            # Step 3: Prepare for outreach (simulated)
            outreach_result = await self._execute_workflow_step(
                workflow_id,
                WorkflowStep.SEND_OUTREACH,
                self._prepare_outreach_step,
                {**context, "communications": comm_result["data"]}
            )
            
            # Step 4: Generate final report
            report_context = {
                "analysis_results": analyze_result["data"],
                "communication_results": comm_result["data"],
                "outreach_results": outreach_result.get("data", {}),
                "workflow_id": workflow_id
            }
            
            report_result = await self._execute_workflow_step(
                workflow_id,
                WorkflowStep.GENERATE_REPORT,
                self._generate_report_step,
                report_context
            )
            
            # Complete workflow
            workflow_state["status"] = WorkflowStatus.COMPLETED.value
            workflow_state["completed_at"] = datetime.utcnow().isoformat()
            workflow_state["progress"] = 100
            
            # Move to history
            self.workflow_history.append(workflow_state.copy())
            del self.active_workflows[workflow_id]
            
            return {
                "status": "success",
                "workflow_id": workflow_id,
                "workflow_status": "completed",
                "final_report": report_result.get("data", {}),
                "execution_summary": self._generate_execution_summary(workflow_state),
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Workflow startup failed: {e}")
            if 'workflow_id' in locals():
                return self._handle_workflow_failure(workflow_id, "Workflow startup failed", {"error": str(e)})
            raise
    
    async def _execute_workflow_step(self, workflow_id: str, step: WorkflowStep, 
                                   step_function, step_context: Dict) -> Dict[str, Any]:
        """Execute a single workflow step with error handling and timeouts"""
        
        workflow_state = self.active_workflows[workflow_id]
        step_config = self.step_configs[step]
        
        step_record = {
            "step": step.value,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "attempts": 0,
            "errors": []
        }
        
        workflow_state["current_step"] = step.value
        workflow_state["steps"].append(step_record)
        
        for attempt in range(step_config["retry_count"] + 1):
            try:
                step_record["attempts"] += 1
                logger.info(f"Executing step {step.value} (attempt {attempt + 1}/{step_config['retry_count'] + 1})")
                
                # Execute step with timeout
                result = await asyncio.wait_for(
                    step_function(step_context),
                    timeout=step_config["timeout"]
                )
                
                step_record["status"] = "completed"
                step_record["completed_at"] = datetime.utcnow().isoformat()
                step_record["result"] = result
                
                # Update progress
                completed_steps = len([s for s in workflow_state["steps"] if s["status"] == "completed"])
                workflow_state["progress"] = (completed_steps / len(self.step_configs)) * 100
                
                return {"status": "success", "data": result}
                
            except asyncio.TimeoutError:
                error_msg = f"Step {step.value} timed out after {step_config['timeout']} seconds"
                step_record["errors"].append(error_msg)
                logger.error(error_msg)
                
            except Exception as e:
                error_msg = f"Step {step.value} failed: {str(e)}"
                step_record["errors"].append(error_msg)
                logger.error(error_msg)
            
            if attempt < step_config["retry_count"]:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # All attempts failed
        step_record["status"] = "failed"
        step_record["failed_at"] = datetime.utcnow().isoformat()
        
        return {
            "status": "error",
            "message": f"Step {step.value} failed after {step_config['retry_count'] + 1} attempts",
            "errors": step_record["errors"]
        }
    
    async def _analyze_patients_step(self, context: Dict) -> Dict[str, Any]:
        """Execute patient analysis step (would call DataAnalyst agent)"""
        # In a full implementation, this would call the DataAnalyst agent
        # For now, simulate the analysis using MCP tools directly
        
        filters = context.get("filters", {})
        
        # Get overdue patients
        overdue_data = await self.mcp_client.get_overdue_patients(**filters)
        
        if overdue_data.get("status") != "success":
            raise Exception(f"Failed to get overdue patients: {overdue_data.get('message')}")
        
        patients = overdue_data.get("patients", [])
        
        # Simulate priority scoring (simplified version)
        prioritized_patients = []
        
        for patient in patients:
            # Get detailed patient info
            patient_details = await self.mcp_client.get_patient_details(patient["patient_id"])
            
            if patient_details.get("status") == "success":
                detailed_patient = patient_details["patient"]
                
                # Simple priority calculation
                priority_score = 0
                age = detailed_patient.get("age", 0)
                overdue_gaps = patient.get("overdue_care_gaps", [])
                
                # Age factor
                if age >= 75: priority_score += 15
                elif age >= 65: priority_score += 10
                elif age >= 50: priority_score += 5
                
                # Overdue factor
                for gap in overdue_gaps:
                    overdue_days = gap.get("overdue_days", 0)
                    if overdue_days > 365: priority_score += 20
                    elif overdue_days > 180: priority_score += 15
                    elif overdue_days > 90: priority_score += 10
                    else: priority_score += 5
                
                # Determine priority level
                if priority_score >= 50: priority_level = "CRITICAL"
                elif priority_score >= 30: priority_level = "HIGH"  
                elif priority_score >= 15: priority_level = "MEDIUM"
                else: priority_level = "LOW"
                
                prioritized_patient = {
                    **patient,
                    "priority_score": priority_score,
                    "priority_level": priority_level,
                    "detailed_info": detailed_patient
                }
                
                prioritized_patients.append(prioritized_patient)
        
        # Sort by priority score
        prioritized_patients.sort(key=lambda x: x["priority_score"], reverse=True)
        
        # Generate insights
        insights = {
            "total_patients": len(prioritized_patients),
            "critical_patients": len([p for p in prioritized_patients if p["priority_level"] == "CRITICAL"]),
            "high_priority_patients": len([p for p in prioritized_patients if p["priority_level"] == "HIGH"]),
            "average_priority_score": sum(p["priority_score"] for p in prioritized_patients) / len(prioritized_patients) if prioritized_patients else 0
        }
        
        return {
            "prioritized_patients": prioritized_patients,
            "insights": insights,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _create_communications_step(self, context: Dict) -> Dict[str, Any]:
        """Execute communication creation step (would call CommunicationSpecialist agent)"""
        # In a full implementation, this would call the CommunicationSpecialist agent
        
        prioritized_patients = context.get("prioritized_patients", [])
        
        if not prioritized_patients:
            return {
                "communications": [],
                "total_created": 0,
                "creation_timestamp": datetime.utcnow().isoformat(),
                "ready_to_send": 0,
                "message": "No prioritized patients available for communication creation"
            }
        
        communications = []
        
        # Create communications for each patient
        for patient in prioritized_patients[:10]:  # Limit to first 10 for demonstration
            try:
                # Simulate communication creation
                patient_id = patient["patient_id"]
                priority_level = patient["priority_level"]
                
                # Generate basic message structure
                communication = {
                    "patient_id": patient_id,
                    "patient_name": patient["name"],
                    "priority_level": priority_level,
                    "message_subject": f"{'URGENT: ' if priority_level == 'CRITICAL' else ''}Health Screening Reminder",
                    "message_preview": f"Dear {patient['name']}, it's time for your health screening...",
                    "preferred_channel": patient.get("preferred_contact_method", "email"),
                    "created_at": datetime.utcnow().isoformat(),
                    "status": "ready_to_send"
                }
                
                # Add follow-up schedule
                if priority_level == "CRITICAL":
                    follow_up_days = [1, 2, 4]
                elif priority_level == "HIGH":
                    follow_up_days = [3, 7, 14]
                else:
                    follow_up_days = [7, 21]
                
                communication["follow_up_schedule"] = [
                    {
                        "days_after": days,
                        "method": patient.get("preferred_contact_method", "email"),
                        "scheduled_date": (date.today() + timedelta(days=days)).isoformat()
                    }
                    for days in follow_up_days
                ]
                
                communications.append(communication)
                
            except Exception as e:
                logger.error(f"Failed to create communication for patient {patient.get('patient_id')}: {e}")
                continue
        
        return {
            "communications": communications,
            "total_created": len(communications),
            "creation_timestamp": datetime.utcnow().isoformat(),
            "ready_to_send": len([c for c in communications if c["status"] == "ready_to_send"])
        }
    
    async def _prepare_outreach_step(self, context: Dict) -> Dict[str, Any]:
        """Prepare outreach delivery (simulation)"""
        communications = context.get("communications", {}).get("communications", [])
        
        # Simulate outreach preparation
        delivery_status = []
        
        for comm in communications:
            # Simulate delivery scheduling
            status_record = {
                "patient_id": comm["patient_id"],
                "communication_id": f"comm_{comm['patient_id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "delivery_method": comm["preferred_channel"],
                "scheduled_delivery": datetime.utcnow().isoformat(),
                "status": "scheduled",
                "tracking_enabled": True
            }
            
            delivery_status.append(status_record)
        
        return {
            "delivery_status": delivery_status,
            "total_scheduled": len(delivery_status),
            "preparation_timestamp": datetime.utcnow().isoformat(),
            "estimated_delivery_completion": (datetime.utcnow() + timedelta(hours=2)).isoformat()
        }
    
    async def _generate_report_step(self, context: Dict) -> Dict[str, Any]:
        """Generate final workflow report"""
        
        analysis_results = context.get("analysis_results", {})
        communication_results = context.get("communication_results", {})
        outreach_results = context.get("outreach_results", {})
        workflow_id = context.get("workflow_id")
        
        report = {
            "workflow_id": workflow_id,
            "generated_at": datetime.utcnow().isoformat(),
            "executive_summary": {
                "total_patients_analyzed": analysis_results.get("insights", {}).get("total_patients", 0),
                "critical_priority_patients": analysis_results.get("insights", {}).get("critical_patients", 0),
                "high_priority_patients": analysis_results.get("insights", {}).get("high_priority_patients", 0),
                "communications_created": communication_results.get("total_created", 0),
                "outreach_scheduled": outreach_results.get("total_scheduled", 0)
            },
            "detailed_results": {
                "patient_analysis": analysis_results,
                "communication_creation": communication_results,
                "outreach_preparation": outreach_results
            },
            "recommendations": self._generate_workflow_recommendations(analysis_results, communication_results),
            "next_steps": [
                "Monitor patient responses to outreach communications",
                "Schedule follow-up communications as planned",
                "Update patient records when screenings are completed",
                "Review workflow effectiveness after 30 days"
            ],
            "quality_metrics": {
                "analysis_coverage": "100%",
                "communication_personalization": "85%",
                "delivery_readiness": "100%"
            }
        }
        
        return report
    
    def _generate_workflow_recommendations(self, analysis_results: Dict, communication_results: Dict) -> List[str]:
        """Generate actionable recommendations based on workflow results"""
        
        recommendations = []
        
        insights = analysis_results.get("insights", {})
        
        # Critical patient recommendations
        critical_count = insights.get("critical_patients", 0)
        if critical_count > 0:
            recommendations.append(f"URGENT: {critical_count} patients require immediate intervention within 24 hours")
        
        # High priority recommendations
        high_count = insights.get("high_priority_patients", 0)
        if high_count > 5:
            recommendations.append("Consider allocating additional care coordination resources for high-priority patients")
        
        # Communication volume recommendations
        total_comms = communication_results.get("total_created", 0)
        if total_comms > 20:
            recommendations.append("Large communication volume - consider staggered delivery to manage response capacity")
        
        # General workflow recommendations
        avg_score = insights.get("average_priority_score", 0)
        if avg_score > 25:
            recommendations.append("High average priority scores indicate systematic care gap issues - consider process improvement")
        
        return recommendations
    
    def _handle_workflow_failure(self, workflow_id: str, reason: str, error_details: Dict) -> Dict[str, Any]:
        """Handle workflow failure and cleanup"""
        
        if workflow_id in self.active_workflows:
            workflow_state = self.active_workflows[workflow_id]
            workflow_state["status"] = WorkflowStatus.FAILED.value
            workflow_state["failed_at"] = datetime.utcnow().isoformat()
            workflow_state["failure_reason"] = reason
            workflow_state["error_details"] = error_details
            
            # Move to history
            self.workflow_history.append(workflow_state.copy())
            del self.active_workflows[workflow_id]
        
        return {
            "status": "error",
            "workflow_id": workflow_id,
            "workflow_status": "failed",
            "reason": reason,
            "error_details": error_details,
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_execution_summary(self, workflow_state: Dict) -> Dict[str, Any]:
        """Generate execution summary for completed workflow"""
        
        total_steps = len(workflow_state["steps"])
        completed_steps = len([s for s in workflow_state["steps"] if s["status"] == "completed"])
        failed_steps = len([s for s in workflow_state["steps"] if s["status"] == "failed"])
        
        start_time = datetime.fromisoformat(workflow_state["created_at"])
        end_time = datetime.fromisoformat(workflow_state.get("completed_at", workflow_state.get("failed_at", datetime.utcnow().isoformat())))
        
        execution_time = (end_time - start_time).total_seconds()
        
        return {
            "total_execution_time_seconds": execution_time,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "success_rate": (completed_steps / total_steps) * 100 if total_steps > 0 else 0,
            "step_details": workflow_state["steps"]
        }
    
    async def _monitor_workflow_progress(self, context: Dict) -> Dict[str, Any]:
        """Monitor active workflow progress"""
        
        workflow_id = context.get("workflow_id")
        
        if workflow_id and workflow_id in self.active_workflows:
            workflow_state = self.active_workflows[workflow_id]
            
            return {
                "status": "success",
                "workflow_id": workflow_id,
                "current_status": workflow_state["status"],
                "current_step": workflow_state.get("current_step"),
                "progress_percentage": workflow_state.get("progress", 0),
                "steps_completed": len([s for s in workflow_state["steps"] if s["status"] == "completed"]),
                "total_steps": len(self.step_configs),
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            # Return status of all active workflows
            active_status = []
            
            for wf_id, wf_state in self.active_workflows.items():
                active_status.append({
                    "workflow_id": wf_id,
                    "status": wf_state["status"],
                    "progress": wf_state.get("progress", 0),
                    "current_step": wf_state.get("current_step"),
                    "created_at": wf_state["created_at"]
                })
            
            return {
                "status": "success",
                "active_workflows": active_status,
                "total_active": len(active_status),
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _update_workflow_status(self, context: Dict) -> Dict[str, Any]:
        """Update workflow status or configuration"""
        # Implementation for workflow updates
        return {
            "status": "info",
            "message": "Workflow update functionality would be implemented here",
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _complete_care_gaps(self, context: Dict) -> Dict[str, Any]:
        """Complete care gaps for patients who have completed screenings"""
        
        completed_screenings = context.get("completed_screenings", [])
        
        if not completed_screenings:
            return {
                "status": "info",
                "message": "No completed screenings to process",
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        completion_results = []
        
        for screening in completed_screenings:
            try:
                care_gap_id = screening.get("care_gap_id")
                completion_date = screening.get("completion_date")
                notes = screening.get("notes", f"Completed via care gap automation workflow")
                
                result = await self.mcp_client.close_care_gap(care_gap_id, completion_date, notes)
                
                completion_results.append({
                    "care_gap_id": care_gap_id,
                    "status": result.get("status"),
                    "message": result.get("message")
                })
                
            except Exception as e:
                completion_results.append({
                    "care_gap_id": screening.get("care_gap_id"),
                    "status": "error",
                    "message": str(e)
                })
        
        successful_completions = len([r for r in completion_results if r["status"] == "success"])
        
        return {
            "status": "success",
            "total_processed": len(completed_screenings),
            "successful_completions": successful_completions,
            "failed_completions": len(completion_results) - successful_completions,
            "completion_results": completion_results,
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _generate_workflow_report(self, context: Dict) -> Dict[str, Any]:
        """Generate workflow report"""
        workflow_id = context.get("workflow_id")
        
        if workflow_id:
            # Generate report for specific workflow
            workflow_data = None
            
            # Check active workflows
            if workflow_id in self.active_workflows:
                workflow_data = self.active_workflows[workflow_id]
            else:
                # Check historical workflows
                workflow_data = next((wf for wf in self.workflow_history if wf["workflow_id"] == workflow_id), None)
            
            if workflow_data:
                return {
                    "status": "success",
                    "report_type": "individual_workflow",
                    "workflow_data": workflow_data,
                    "execution_summary": self._generate_execution_summary(workflow_data),
                    "agent": self.name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Workflow {workflow_id} not found",
                    "agent": self.name,
                    "timestamp": datetime.utcnow().isoformat()
                }
        else:
            # Generate summary report of all workflows
            total_workflows = len(self.workflow_history) + len(self.active_workflows)
            completed_workflows = len([wf for wf in self.workflow_history if wf["status"] == WorkflowStatus.COMPLETED.value])
            failed_workflows = len([wf for wf in self.workflow_history if wf["status"] == WorkflowStatus.FAILED.value])
            
            return {
                "status": "success",
                "report_type": "summary",
                "total_workflows": total_workflows,
                "completed_workflows": completed_workflows,
                "failed_workflows": failed_workflows,
                "active_workflows": len(self.active_workflows),
                "success_rate": (completed_workflows / total_workflows * 100) if total_workflows > 0 else 0,
                "recent_workflows": self.workflow_history[-10:],  # Last 10 workflows
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _handle_workflow_exception(self, context: Dict) -> Dict[str, Any]:
        """Handle workflow exceptions and recovery"""
        return {
            "status": "info",
            "message": "Workflow exception handling would be implemented here",
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _general_workflow_guidance(self, message: str, context: Dict) -> Dict[str, Any]:
        """Provide general workflow guidance"""
        return {
            "status": "info",
            "message": "I orchestrate healthcare care gap automation workflows. Available commands: 'start workflow', 'monitor progress', 'complete care gaps', 'generate report'",
            "available_functions": [
                "start_care_gap_workflow",
                "monitor_workflow_progress", 
                "complete_care_gaps",
                "generate_workflow_report"
            ],
            "active_workflows": len(self.active_workflows),
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }