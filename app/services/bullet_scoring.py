import logging
import re
import json
from app.services.llm_service import ask_ai

logger = logging.getLogger(__name__)

class BulletScoringService:
    """
    Evaluates individual resume bullets (achievements) based on production-grade rubrics.
    Scores on: Action Verbs, Metrics, and Seniority Alignment.
    """

    STRONG_VERBS = {
        "architected", "spearheaded", "orchestrated", "engineered", "optimized",
        "pioneered", "automated", "mentored", "surpassed", "transformed"
    }
    
    WEAK_VERBS = {
        "helped", "assisted", "worked", "did", "responsible", "managed",
        "participated", "was", "showed", "looked"
    }

    @staticmethod
    async def score_bullet(bullet_text, seniority_level="senior"):
        """
        Analyzes a single bullet point.
        Returns a score (0-100) and specific feedback/rewrite suggestions.
        """
        if not bullet_text or len(bullet_text) < 10:
            return {"score": 0, "feedback": "Bullet is too short to be impactful.", "suggestion": "Add more detail about what you achieved."}

        # 1. Linguistic Analysis (Basic)
        has_metric = bool(re.search(r'\d+%|\$\d+|\d+\s*users|reduced|increased', bullet_text, re.I))
        
        words = bullet_text.lower().split()
        first_word = words[0].strip('., ') if words else ""
        
        verb_score = 0
        if first_word in BulletScoringService.STRONG_VERBS:
            verb_score = 100
        elif first_word in BulletScoringService.WEAK_VERBS:
            verb_score = 30
        else:
            verb_score = 70 # Neutral/Unknown verb

        # 2. AI-Powered Deep Scoring and Rewrite
        prompt = f"""
Analyze this resume achievement bullet for a {seniority_level} role:
"{bullet_text}"

Criteria:
- Action Verb Strength
- Quantifiable Impact (Metrics)
- Result-oriented phrasing

Respond ONLY with JSON:
{{
    "rubric_score": (0-100),
    "feedback": "...",
    "suggestion": "A high-impact rewritten version of the bullet",
    "metrics_found": (true/false)
}}
"""
        try:
            response = await ask_ai(
                prompt=prompt,
                system_prompt="You are an expert career coach and professional resume editor.",
                max_tokens=250,
                temperature=0.0
            )
            
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            
            analysis = json.loads(response)
            
            # Weighted average with our heuristic
            final_score = (analysis['rubric_score'] * 0.7) + (verb_score * 0.3)
            if not has_metric and analysis['metrics_found']:
                final_score -= 10 # Penalize lack of hard numbers if AI didn't find them either
            
            return {
                "score": round(final_score),
                "feedback": analysis['feedback'],
                "suggestion": analysis['suggestion']
            }
        except Exception as e:
            logger.error(f"Bullet scoring failed: {str(e)}")
            return {"score": 50, "feedback": "Quality analysis temporarily unavailable.", "suggestion": bullet_text}

    @staticmethod
    async def score_experience(experience_list, seniority_level="senior"):
        """
        Scores all bullets in an experience list. Returns list of enhancements.
        """
        all_results = []
        for exp in experience_list:
            achievements = exp.get('achievements', [])
            role_results = []
            for ach in achievements:
                res = await BulletScoringService.score_bullet(ach, seniority_level)
                role_results.append({
                    "original": ach,
                    **res
                })
            all_results.append({
                "role": exp.get('role'),
                "bullets": role_results
            })
        return all_results
