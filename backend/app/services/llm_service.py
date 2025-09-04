"""
LLM Service for healthcare natural language processing
Handles OpenAI API integration for understanding user prompts about screening tests
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta

import openai
from ..config.settings import settings

logger = logging.getLogger(__name__)


class HealthcareLLMService:
    """Service for processing healthcare-related natural language queries using OpenAI"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Common screening tests mapping
        self.screening_tests = {
            "mammography": ["mammogram", "mammography", "breast cancer screening", "breast scan"],
            "colonoscopy": ["colonoscopy", "colon cancer screening", "colorectal screening", "colon scan"],
            "pap_smear": ["pap smear", "pap test", "cervical cancer screening", "cervical screening"],
            "blood_pressure_check": ["blood pressure", "bp check", "hypertension screening"],
            "cholesterol_screening": ["cholesterol", "lipid panel", "cholesterol test", "lipid screening"],
            "diabetes_screening": ["diabetes", "blood sugar", "glucose test", "a1c", "hemoglobin a1c"],
            "bone_density_scan": ["bone density", "dexa scan", "osteoporosis screening", "bone scan"],
            "eye_exam": ["eye exam", "vision test", "ophthalmology", "eye screening"],
            "skin_cancer_screening": ["skin cancer", "dermatology", "mole check", "skin screening"],
            "prostate_screening": ["prostate", "psa test", "prostate cancer screening"],
            "breast_self_exam": ["breast self exam", "bse", "breast check"],
            "cervical_cancer_screening": ["cervical cancer", "hpv test", "cervical screening"],
            "lung_cancer_screening": ["lung cancer", "chest ct", "lung screening", "pulmonary screening"],
            "hepatitis_b_screening": ["hepatitis b", "hep b", "hepatitis screening"],
            "osteoporosis_screening": ["osteoporosis", "bone health", "fracture risk"]
        }
    
    async def parse_screening_request(self, user_prompt: str) -> Dict[str, Any]:
        """
        Parse user prompt to extract screening test requirements and patient criteria
        """
        try:
            system_prompt = """You are a healthcare AI assistant that helps extract screening test information from natural language queries. 

Your job is to:
1. Identify what screening test(s) the user is asking about
2. Extract any specific patient criteria or filters
3. Determine the urgency or priority level
4. Extract time-related criteria (e.g., "last 3 months", "overdue patients")

Available screening tests:
- mammography (breast cancer screening)
- colonoscopy (colorectal cancer screening) 
- pap_smear (cervical cancer screening)
- blood_pressure_check
- cholesterol_screening
- diabetes_screening
- bone_density_scan
- eye_exam
- skin_cancer_screening
- prostate_screening
- breast_self_exam
- cervical_cancer_screening
- lung_cancer_screening
- hepatitis_b_screening
- osteoporosis_screening

Respond with a JSON object containing:
{
  "screening_tests": ["test1", "test2"],
  "patient_criteria": {
    "age_range": [min, max] or null,
    "gender": "male"|"female"|null,
    "risk_factors": ["risk1", "risk2"] or [],
    "priority_level": "urgent"|"high"|"medium"|"low"|null
  },
  "time_criteria": {
    "overdue_only": true|false,
    "time_period": "3_months"|"6_months"|"1_year"|null,
    "specific_date_range": null
  },
  "query_intent": "list_pending_patients"|"schedule_appointments"|"analyze_gaps"|"general_inquiry",
  "urgency": "immediate"|"high"|"normal"|"low",
  "extracted_keywords": ["keyword1", "keyword2"]
}

Examples:
- "Show me patients who need mammograms" -> {"screening_tests": ["mammography"], "query_intent": "list_pending_patients"}
- "Find urgent colonoscopy patients from last 3 months" -> {"screening_tests": ["colonoscopy"], "time_criteria": {"time_period": "3_months"}, "urgency": "high"}
- "Diabetes screening for seniors" -> {"screening_tests": ["diabetes_screening"], "patient_criteria": {"age_range": [65, null]}}
"""

            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Try to extract JSON from the response
            try:
                # Look for JSON in the response
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    parsed_data = json.loads(json_match.group())
                else:
                    # Fallback parsing
                    parsed_data = self._fallback_parse(user_prompt)
                
                # Validate and clean the parsed data
                return self._validate_parsed_data(parsed_data, user_prompt)
                
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM JSON response: {response_text}")
                return self._fallback_parse(user_prompt)
                
        except Exception as e:
            logger.error(f"LLM parsing error: {e}")
            return self._fallback_parse(user_prompt)
    
    def _fallback_parse(self, user_prompt: str) -> Dict[str, Any]:
        """Fallback parsing when LLM fails"""
        user_prompt_lower = user_prompt.lower()
        
        # Extract screening tests using keyword matching
        detected_tests = []
        for test_name, keywords in self.screening_tests.items():
            if any(keyword.lower() in user_prompt_lower for keyword in keywords):
                detected_tests.append(test_name)
        
        # Extract basic criteria
        overdue_only = any(word in user_prompt_lower for word in ['overdue', 'pending', 'due', 'missing'])
        urgency = "high" if any(word in user_prompt_lower for word in ['urgent', 'priority', 'immediate']) else "normal"
        
        # Time period extraction
        time_period = None
        if "3 month" in user_prompt_lower:
            time_period = "3_months"
        elif "6 month" in user_prompt_lower:
            time_period = "6_months"
        elif "year" in user_prompt_lower or "12 month" in user_prompt_lower:
            time_period = "1_year"
        
        return {
            "screening_tests": detected_tests or ["all"],
            "patient_criteria": {
                "age_range": None,
                "gender": None,
                "risk_factors": [],
                "priority_level": None
            },
            "time_criteria": {
                "overdue_only": overdue_only,
                "time_period": time_period,
                "specific_date_range": None
            },
            "query_intent": "list_pending_patients",
            "urgency": urgency,
            "extracted_keywords": detected_tests,
            "fallback_used": True
        }
    
    def _validate_parsed_data(self, data: Dict[str, Any], original_prompt: str) -> Dict[str, Any]:
        """Validate and clean parsed data"""
        # Ensure required fields exist
        validated = {
            "screening_tests": data.get("screening_tests", []),
            "patient_criteria": data.get("patient_criteria", {}),
            "time_criteria": data.get("time_criteria", {}),
            "query_intent": data.get("query_intent", "list_pending_patients"),
            "urgency": data.get("urgency", "normal"),
            "extracted_keywords": data.get("extracted_keywords", []),
            "original_prompt": original_prompt,
            "parsed_at": datetime.utcnow().isoformat()
        }
        
        # Validate screening tests against known tests
        valid_tests = []
        for test in validated["screening_tests"]:
            if test in self.screening_tests or test == "all":
                valid_tests.append(test)
            else:
                # Try to find closest match
                for known_test, keywords in self.screening_tests.items():
                    if any(keyword in test.lower() for keyword in keywords):
                        valid_tests.append(known_test)
                        break
        
        validated["screening_tests"] = valid_tests or ["all"]
        
        # Ensure nested dictionaries have defaults
        validated["patient_criteria"] = {
            "age_range": validated["patient_criteria"].get("age_range"),
            "gender": validated["patient_criteria"].get("gender"),
            "risk_factors": validated["patient_criteria"].get("risk_factors", []),
            "priority_level": validated["patient_criteria"].get("priority_level")
        }
        
        validated["time_criteria"] = {
            "overdue_only": validated["time_criteria"].get("overdue_only", True),
            "time_period": validated["time_criteria"].get("time_period"),
            "specific_date_range": validated["time_criteria"].get("specific_date_range")
        }
        
        return validated
    
    async def generate_patient_summary(self, patients: List[Dict[str, Any]], query_context: Dict[str, Any]) -> str:
        """Generate a natural language summary of patient results"""
        try:
            if not patients:
                return "No patients found matching the specified criteria."
            
            system_prompt = """You are a healthcare AI assistant that summarizes patient care gap data. 
Create a concise, professional summary that highlights:
1. Number of patients found
2. Priority distribution
3. Key insights about overdue screenings
4. Recommended next actions

Keep the summary informative but brief (2-3 sentences)."""
            
            # Prepare patient data summary
            total_patients = len(patients)
            urgent_count = sum(1 for p in patients if p.get('priority_level') == 'urgent')
            high_count = sum(1 for p in patients if p.get('priority_level') == 'high')
            
            screening_types = [p.get('screening_type', 'unknown') for p in patients]
            most_common_screening = max(set(screening_types), key=screening_types.count) if screening_types else 'unknown'
            
            data_summary = f"""
Patient Summary:
- Total patients: {total_patients}
- Urgent priority: {urgent_count}  
- High priority: {high_count}
- Most common overdue screening: {most_common_screening}
- Query: {query_context.get('original_prompt', 'N/A')}
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": data_summary}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return f"Found {len(patients)} patients matching your criteria. Review the detailed results below."