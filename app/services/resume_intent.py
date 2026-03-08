import logging
import json
from app.services.llm_service import ask_ai

logger = logging.getLogger(__name__)

class ResumeIntentService:
    """
    Infers the user's career intent and target environment.
    Used to condition resume generation and optimization for specific strategies.
    """

    @staticmethod
    async def infer_intent(profile_data, target_role=None, job_description=None):
        """
        Uses AI to classify the user's intent.
        Returns a dict with:
        - career_stage: (switch, promotion, entry, career_pivot)
        - environment: (startup, enterprise, mid-market)
        - work_mode: (remote, hybrid, onsite)
        - risk_profile: (bold, conservative, balanced)
        - content_focus: (technical, leadership, product, growth)
        """
        
        # Simplified context for AI inference
        context = {
            "current_bio": profile_data.get('bio', ''),
            "target_role": target_role,
            "has_jd": bool(job_description)
        }
        
        prompt = f"""
Analyze the user's career intent based on their bio and target role.

Bio: {context['current_bio']}
Target Role: {context['target_role']}
Job Description Snippet: {job_description[:500] if job_description else 'N/A'}

Analyze the following dimensions:
1. Career Stage Strategy: 
   - 'switch': Same role, different company. Focus on transferrable skills and immediate impact.
   - 'promotion': Moving up (e.g., Senior to Lead). Focus on leadership, strategy, and mentorship.
   - 'pivot': Changing fields. Focus on core logic and adaptability.
2. Environment: 
   - 'startup': High growth, multi-hat, rapid execution. Tone: Bold, versatile.
   - 'enterprise': Scalable systems, process, compliance, cross-functional. Tone: Structured, professional.
3. Work Mode:
   - 'remote': Focus on async communication, self-management, and digital tools.
   - 'onsite': Focus on collaboration and physical presence.

Respond ONLY with JSON:
{{
    "career_stage": "promotion|switch|pivot",
    "environment": "startup|enterprise",
    "work_mode": "remote|hybrid|onsite",
    "risk_profile": "bold|conservative",
    "content_focus": "leadership|technical|execution",
    "logic": "brief explanation of why this intent was inferred"
}}
"""

        try:
            response = await ask_ai(
                prompt=prompt,
                system_prompt="You are a career strategist specializing in intent classification.",
                max_tokens=300,
                temperature=0.0 # Deterministic classification
            )
            
            # Clean response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            
            intent = json.loads(response)
            return intent
        except Exception as e:
            logger.error(f"Intent inference failed: {str(e)}")
            # Fallback to safe defaults
            return {
                "career_stage": "switch",
                "environment": "enterprise",
                "work_mode": "hybrid",
                "risk_profile": "conservative",
                "content_focus": "execution",
                "logic": "fallback default"
            }
