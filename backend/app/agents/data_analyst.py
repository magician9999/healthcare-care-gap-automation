import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, date
import math

from .base_agent import BaseHealthcareAgent

logger = logging.getLogger(__name__)


class DataAnalystAgent(BaseHealthcareAgent):
    """
    Specialized AutoGen agent for analyzing patient data and prioritizing care gaps
    Uses MCP tools to analyze patient lists and prioritize by medical urgency
    """
    
    def __init__(self):
        system_message = """You are a Clinical Data Analyst AI specializing in healthcare care gap analysis. 
        Your role is to:
        1. Analyze patient lists from EHR systems
        2. Prioritize patients by medical urgency and risk factors
        3. Consider screening type importance and overdue duration
        4. Provide clinical reasoning for prioritization decisions
        5. Generate actionable insights for care teams
        
        You have access to healthcare MCP tools for patient data retrieval and analysis.
        Always provide evidence-based recommendations with clear clinical justification."""
        
        super().__init__(
            name="DataAnalystAgent",
            role="Clinical Data Analyst",
            system_message=system_message
        )
        
        # Medical screening priority levels
        self.screening_priorities = {
            # Critical screenings
            "mammogram": {"priority": 9, "urgency_multiplier": 1.2, "category": "cancer_screening"},
            "colonoscopy": {"priority": 9, "urgency_multiplier": 1.2, "category": "cancer_screening"},
            "pap_smear": {"priority": 8, "urgency_multiplier": 1.1, "category": "cancer_screening"},
            "prostate_exam": {"priority": 8, "urgency_multiplier": 1.1, "category": "cancer_screening"},
            
            # Cardiovascular
            "blood_pressure_check": {"priority": 7, "urgency_multiplier": 1.0, "category": "cardiovascular"},
            "cholesterol_screening": {"priority": 6, "urgency_multiplier": 0.9, "category": "cardiovascular"},
            
            # Metabolic
            "diabetes_screening": {"priority": 7, "urgency_multiplier": 1.0, "category": "metabolic"},
            "bone_density_scan": {"priority": 5, "urgency_multiplier": 0.8, "category": "metabolic"},
            
            # Routine
            "eye_exam": {"priority": 4, "urgency_multiplier": 0.7, "category": "routine"},
            "hearing_test": {"priority": 3, "urgency_multiplier": 0.6, "category": "routine"}
        }
        
        # Risk factor weights
        self.risk_factor_weights = {
            "family history of heart disease": 1.3,
            "family history of cancer": 1.4,
            "smoker": 1.5,
            "diabetes": 1.3,
            "high blood pressure": 1.2,
            "high cholesterol": 1.2,
            "obesity": 1.1,
            "age-related risks": 1.1
        }
    
    async def process_message(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process data analysis requests with natural language understanding"""
        self.add_to_conversation("user", message, context)
        
        try:
            # First try to process as natural language healthcare query
            if self._is_healthcare_query(message):
                logger.info(f"Processing as natural language healthcare query: {message}")
                result = await self.process_natural_language_query(message)
                
                if result["status"] == "success":
                    # Enhance with priority analysis
                    patients = result["patients"]
                    enhanced_patients = []
                    
                    for patient in patients:
                        priority_score = self._calculate_patient_priority_score({
                            "age": patient.get("age", 0),
                            "overdue_care_gaps": [{
                                "screening_type": patient.get("screening_type", ""),
                                "overdue_days": patient.get("overdue_days", 0),
                                "priority_level": patient.get("priority_level", "medium")
                            }],
                            "risk_factors": patient.get("risk_factors", "")
                        })
                        
                        enhanced_patient = {
                            **patient,
                            "priority_score": priority_score["total_score"],
                            "clinical_reasoning": priority_score["reasoning"],
                            "recommended_actions": priority_score["recommended_actions"]
                        }
                        enhanced_patients.append(enhanced_patient)
                    
                    # Sort by priority score
                    enhanced_patients.sort(key=lambda x: x["priority_score"], reverse=True)
                    
                    result["patients"] = enhanced_patients
                    result["agent_analysis"] = "Enhanced with clinical priority scoring"
                    
                self.add_to_conversation("assistant", json.dumps(result), {"query_type": "natural_language"})
                return result
            
            # Traditional analysis request
            request_type = self._parse_request_type(message)
            
            if request_type == "prioritize_overdue_patients":
                result = await self._prioritize_overdue_patients(context or {})
            elif request_type == "analyze_patient_cohort":
                result = await self._analyze_patient_cohort(context or {})
            elif request_type == "risk_assessment":
                result = await self._perform_risk_assessment(context or {})
            else:
                result = await self._general_analysis(message, context or {})
            
            self.add_to_conversation("assistant", json.dumps(result), {"request_type": request_type})
            return result
            
        except Exception as e:
            logger.error(f"DataAnalystAgent processing failed: {e}")
            error_result = {
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.add_to_conversation("assistant", json.dumps(error_result), {"error": True})
            return error_result
    
    def _is_healthcare_query(self, message: str) -> bool:
        """Determine if message is a natural language healthcare query"""
        message_lower = message.lower()
        
        # Healthcare screening keywords
        healthcare_keywords = [
            "mammogram", "mammography", "breast cancer", "breast screening",
            "colonoscopy", "colon cancer", "colorectal screening",
            "pap smear", "pap test", "cervical cancer",
            "blood pressure", "bp check", "hypertension",
            "cholesterol", "lipid panel", "lipid screening",
            "diabetes", "blood sugar", "glucose", "a1c",
            "bone density", "dexa scan", "osteoporosis",
            "eye exam", "vision test", "ophthalmology",
            "skin cancer", "dermatology", "mole check",
            "prostate", "psa test",
            "screening", "test", "checkup", "exam"
        ]
        
        # Patient query patterns
        query_patterns = [
            "show me", "find", "list", "who need", "patients with",
            "overdue", "pending", "due for", "need"
        ]
        
        has_healthcare_term = any(keyword in message_lower for keyword in healthcare_keywords)
        has_query_pattern = any(pattern in message_lower for pattern in query_patterns)
        
        return has_healthcare_term and has_query_pattern
    
    def _parse_request_type(self, message: str) -> str:
        """Parse the type of analysis request"""
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ["prioritize", "urgent", "overdue"]):
            return "prioritize_overdue_patients"
        elif any(keyword in message_lower for keyword in ["cohort", "analyze", "population"]):
            return "analyze_patient_cohort"
        elif any(keyword in message_lower for keyword in ["risk", "assessment", "high-risk"]):
            return "risk_assessment"
        else:
            return "general_analysis"
    
    async def _prioritize_overdue_patients(self, context: Dict) -> Dict[str, Any]:
        """Prioritize overdue patients by medical urgency"""
        try:
            # Get filters from context
            filters = context.get("filters", {})
            
            # Retrieve overdue patients
            overdue_data = await self.mcp_client.get_overdue_patients(**filters)
            
            if overdue_data.get("status") != "success":
                return {
                    "status": "error",
                    "message": f"Failed to retrieve overdue patients: {overdue_data.get('message')}",
                    "agent": self.name
                }
            
            patients = overdue_data.get("patients", [])
            
            # Calculate priority scores for each patient
            prioritized_patients = []
            
            for patient in patients:
                # Get detailed patient information for better analysis
                patient_details = await self.mcp_client.get_patient_details(patient["patient_id"])
                
                if patient_details.get("status") == "success":
                    detailed_patient = patient_details["patient"]
                    priority_score = self._calculate_patient_priority_score(detailed_patient)
                    
                    prioritized_patient = {
                        **patient,
                        "priority_score": priority_score["total_score"],
                        "priority_level": priority_score["priority_level"],
                        "clinical_reasoning": priority_score["reasoning"],
                        "recommended_actions": priority_score["recommended_actions"],
                        "risk_factors": detailed_patient.get("risk_factors"),
                        "total_care_gaps": detailed_patient.get("total_care_gaps", 0),
                        "open_care_gaps": detailed_patient.get("open_care_gaps", 0)
                    }
                    
                    prioritized_patients.append(prioritized_patient)
            
            # Sort by priority score (highest first)
            prioritized_patients.sort(key=lambda x: x["priority_score"], reverse=True)
            
            # Generate summary insights
            insights = self._generate_cohort_insights(prioritized_patients)
            
            return {
                "status": "success",
                "analysis_type": "patient_prioritization",
                "total_patients": len(prioritized_patients),
                "prioritized_patients": prioritized_patients,
                "insights": insights,
                "agent": self.name,
                "timestamp": datetime.utcnow().isoformat(),
                "filters_applied": filters
            }
            
        except Exception as e:
            logger.error(f"Patient prioritization failed: {e}")
            raise
    
    def _calculate_patient_priority_score(self, patient: Dict) -> Dict[str, Any]:
        """Calculate comprehensive priority score for a patient"""
        
        base_score = 0
        reasoning_components = []
        recommended_actions = []
        
        # Age-based scoring
        age = patient.get("age", 0)
        age_score = 0
        if age >= 75:
            age_score = 15
            reasoning_components.append(f"Advanced age ({age}): +15 points")
        elif age >= 65:
            age_score = 10
            reasoning_components.append(f"Senior age ({age}): +10 points")
        elif age >= 50:
            age_score = 5
            reasoning_components.append(f"Middle age ({age}): +5 points")
        
        base_score += age_score
        
        # Care gap analysis
        care_gap_score = 0
        overdue_gaps = patient.get("overdue_care_gaps", [])
        
        for gap in overdue_gaps:
            screening_type = gap.get("screening_type", "").lower()
            overdue_days = gap.get("overdue_days", 0)
            priority_level = gap.get("priority_level", "medium")
            
            # Base screening priority
            screening_info = self.screening_priorities.get(screening_type, 
                {"priority": 5, "urgency_multiplier": 1.0, "category": "routine"})
            
            gap_score = screening_info["priority"]
            
            # Overdue duration multiplier
            if overdue_days > 365:
                gap_score *= 2.0
                reasoning_components.append(f"{screening_type}: Critical overdue (>1 year, {overdue_days} days)")
                recommended_actions.append(f"URGENT: Schedule {screening_type} immediately")
            elif overdue_days > 180:
                gap_score *= 1.5
                reasoning_components.append(f"{screening_type}: Significantly overdue ({overdue_days} days)")
                recommended_actions.append(f"HIGH PRIORITY: Schedule {screening_type} within 2 weeks")
            elif overdue_days > 90:
                gap_score *= 1.2
                reasoning_components.append(f"{screening_type}: Moderately overdue ({overdue_days} days)")
                recommended_actions.append(f"Schedule {screening_type} within 4 weeks")
            
            # Priority level adjustment
            priority_multipliers = {"urgent": 1.5, "high": 1.3, "medium": 1.0, "low": 0.8}
            gap_score *= priority_multipliers.get(priority_level, 1.0)
            
            care_gap_score += gap_score
        
        base_score += care_gap_score
        
        # Risk factors analysis
        risk_score = 0
        risk_factors = patient.get("risk_factors", "") or ""
        
        if risk_factors:
            for risk_factor, weight in self.risk_factor_weights.items():
                if risk_factor.lower() in risk_factors.lower():
                    risk_adjustment = 5 * weight
                    risk_score += risk_adjustment
                    reasoning_components.append(f"Risk factor ({risk_factor}): +{risk_adjustment:.1f} points")
        
        base_score += risk_score
        
        # Total open care gaps impact
        open_gaps = patient.get("open_care_gaps", 0)
        if open_gaps > 3:
            gap_burden_score = open_gaps * 2
            base_score += gap_burden_score
            reasoning_components.append(f"High care gap burden ({open_gaps} gaps): +{gap_burden_score} points")
            recommended_actions.append("Consider comprehensive care coordination")
        
        # Determine priority level
        if base_score >= 50:
            priority_level = "CRITICAL"
            recommended_actions.insert(0, "IMMEDIATE INTERVENTION REQUIRED")
        elif base_score >= 30:
            priority_level = "HIGH"
            recommended_actions.insert(0, "Priority outreach within 48 hours")
        elif base_score >= 15:
            priority_level = "MEDIUM"
            recommended_actions.insert(0, "Outreach within 1 week")
        else:
            priority_level = "LOW"
            recommended_actions.insert(0, "Standard outreach schedule")
        
        return {
            "total_score": round(base_score, 2),
            "priority_level": priority_level,
            "reasoning": reasoning_components,
            "recommended_actions": recommended_actions,
            "score_breakdown": {
                "age_score": age_score,
                "care_gap_score": round(care_gap_score, 2),
                "risk_factor_score": round(risk_score, 2),
                "total": round(base_score, 2)
            }
        }
    
    def _generate_cohort_insights(self, prioritized_patients: List[Dict]) -> Dict[str, Any]:
        """Generate insights about the patient cohort"""
        
        if not prioritized_patients:
            return {"message": "No patients to analyze"}
        
        # Priority distribution
        priority_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        
        # Age distribution
        age_ranges = {"18-39": 0, "40-64": 0, "65-74": 0, "75+": 0}
        
        # Screening type analysis
        screening_types = {}
        
        # Risk factor analysis
        risk_factors = {}
        
        total_score = 0
        
        for patient in prioritized_patients:
            # Priority distribution
            priority_level = patient.get("priority_level", "LOW")
            priority_counts[priority_level] += 1
            
            # Age distribution
            age = patient.get("age", 0)
            if age < 40:
                age_ranges["18-39"] += 1
            elif age < 65:
                age_ranges["40-64"] += 1
            elif age < 75:
                age_ranges["65-74"] += 1
            else:
                age_ranges["75+"] += 1
            
            # Screening types
            for gap in patient.get("overdue_care_gaps", []):
                screening_type = gap.get("screening_type")
                if screening_type:
                    screening_types[screening_type] = screening_types.get(screening_type, 0) + 1
            
            # Risk factors
            patient_risks = patient.get("risk_factors", "") or ""
            if patient_risks:
                for risk_factor in self.risk_factor_weights.keys():
                    if risk_factor.lower() in patient_risks.lower():
                        risk_factors[risk_factor] = risk_factors.get(risk_factor, 0) + 1
            
            total_score += patient.get("priority_score", 0)
        
        # Calculate statistics
        avg_score = total_score / len(prioritized_patients) if prioritized_patients else 0
        
        # Generate recommendations
        recommendations = []
        
        if priority_counts["CRITICAL"] > 0:
            recommendations.append(f"URGENT: {priority_counts['CRITICAL']} patients require immediate intervention")
        
        if priority_counts["HIGH"] > 5:
            recommendations.append("Consider additional care coordination resources for high-priority patients")
        
        # Most common overdue screening
        if screening_types:
            most_common_screening = max(screening_types.items(), key=lambda x: x[1])
            recommendations.append(f"Focus outreach campaign on {most_common_screening[0]} ({most_common_screening[1]} patients)")
        
        # Risk factor insights
        if risk_factors:
            high_risk_factor = max(risk_factors.items(), key=lambda x: x[1])
            recommendations.append(f"High prevalence of {high_risk_factor[0]} ({high_risk_factor[1]} patients)")
        
        return {
            "cohort_size": len(prioritized_patients),
            "average_priority_score": round(avg_score, 2),
            "priority_distribution": priority_counts,
            "age_distribution": age_ranges,
            "common_overdue_screenings": dict(sorted(screening_types.items(), key=lambda x: x[1], reverse=True)[:5]),
            "prevalent_risk_factors": dict(sorted(risk_factors.items(), key=lambda x: x[1], reverse=True)[:5]),
            "key_recommendations": recommendations,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _analyze_patient_cohort(self, context: Dict) -> Dict[str, Any]:
        """Analyze a specific patient cohort"""
        # This would implement cohort-specific analysis
        # For now, delegate to prioritization analysis
        return await self._prioritize_overdue_patients(context)
    
    async def _perform_risk_assessment(self, context: Dict) -> Dict[str, Any]:
        """Perform risk assessment analysis"""
        patient_id = context.get("patient_id")
        
        if patient_id:
            # Single patient risk assessment
            patient_details = await self.mcp_client.get_patient_details(patient_id)
            
            if patient_details.get("status") == "success":
                priority_score = self._calculate_patient_priority_score(patient_details["patient"])
                
                return {
                    "status": "success",
                    "analysis_type": "individual_risk_assessment",
                    "patient_id": patient_id,
                    "risk_assessment": priority_score,
                    "agent": self.name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to retrieve patient details: {patient_details.get('message')}",
                    "agent": self.name
                }
        else:
            # Population risk assessment
            return await self._prioritize_overdue_patients(context)
    
    async def _general_analysis(self, message: str, context: Dict) -> Dict[str, Any]:
        """Handle general analysis requests"""
        return {
            "status": "info",
            "message": "I specialize in patient prioritization and risk assessment. Please specify: 'prioritize overdue patients', 'analyze cohort', or 'risk assessment'",
            "available_analyses": [
                "prioritize_overdue_patients",
                "analyze_patient_cohort", 
                "risk_assessment"
            ],
            "agent": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }