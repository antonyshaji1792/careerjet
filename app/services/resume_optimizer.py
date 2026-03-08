from app.services.llm_service import ask_ai
import logging
import json

logger = logging.getLogger(__name__)

class ResumeOptimizerService:
    """Optimizes resumes for specific job descriptions."""
    
    async def optimize(self, resume_json, job_description):
        prompt = f"""
        Optimize this resume for this job description:
        Resume: {json.dumps(resume_json)}
        Job Description: {job_description}
        
        Provide ATS score and tailored content.
        """
        try:
            response = await ask_ai(prompt, system_prompt="You are an ATS expert.")
            # Parsing logic...
            return {"optimized": True, "details": response}
        except Exception as e:
            logger.error(f"Optimization failed: {str(e)}")
            return None
