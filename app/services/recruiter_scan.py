import logging
import json
from app.services.llm_service import ask_ai

logger = logging.getLogger(__name__)

class RecruiterScanService:
    """
    Simulates the human recruiter "7-second scan" of a resume.
    Focuses on visual hierarchy, hooks, and immediate role alignment.
    """

    @staticmethod
    async def simulate_scan(resume_data):
        """
        Uses AI to perform a simulated human scan.
        """
        # Focus on the 'top' of the resume - Header, Summary, and first half of most recent job.
        top_content = {
            "header": resume_data.get('header', {}),
            "summary": resume_data.get('summary', ''),
            "recent_role": resume_data.get('experience', [{}])[0] if resume_data.get('experience') else {}
        }
        
        prompt = f"""
Act as a busy Technical Recruiter. You have 7 seconds to look at this candidate:
Header/Title: {json.dumps(top_content['header'])}
Summary: {top_content['summary']}
Most Recent Role: {top_content['recent_role'].get('role')} at {top_content['recent_role'].get('company')}
Top Bullets: {json.dumps(top_content['recent_role'].get('achievements', [])[:2])}

Analyze based on these Recruiter Scan criteria:
1. Role Clarity (0-10): Can I tell within 2 seconds what their job title is?
2. The 'Hook' (0-10): Does the summary or first bullet make me want to read more?
3. Impact Density (0-10): Are there numbers or outcomes visible at a glance?
4. Section Priority: Which section did I notice first?

Respond ONLY with JSON:
{{
    "clarity_score": (integer),
    "hook_score": (integer),
    "impact_score": (integer),
    "first_impression": "Brief impression (e.g., 'Strong Lead', 'Generic Developer', 'Mismatched Title')",
    "missing_hooks": ["...", "..."],
    "priority_feedback": "Which sections were most/least visible during a scan",
    "the_7_second_verdict": "Keep/Pass reason"
}}
"""
        try:
            response = await ask_ai(
                prompt=prompt,
                system_prompt="You are a senior recruiter at a top tech company known for scanning resumes extremely quickly.",
                max_tokens=400,
                temperature=0.0
            )

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            
            scan_result = json.loads(response)
            return scan_result
        except Exception as e:
            logger.error(f"Recruiter scan simulation failed: {str(e)}")
            return {
                "clarity_score": 0,
                "hook_score": 0,
                "impact_score": 0,
                "first_impression": "Analysis Error",
                "missing_hooks": [],
                "priority_feedback": "Unable to analyze.",
                "the_7_second_verdict": "N/A"
            }
