import re
import logging
from app.services.ai_metering_service import AIMeteringService
from app.services.prompt_registry import PromptRegistryService

logger = logging.getLogger(__name__)

class HybridEnhancementService:
    """
    Implements Progressive AI Enhancement:
    1. Rule-based checks first (fast, free).
    2. AI reasoning only when heuristics are insufficient.
    3. Prevents redundant AI calls for cosmetic or simple structural changes.
    """

    STRONG_VERBS = {
        "led", "managed", "developed", "architected", "optimized", "reduced",
        "increased", "implemented", "spearheaded", "designed", "built"
    }

    @staticmethod
    async def improve_bullet(user_id, text, context="resume bullet"):
        """
        Attempts to improve a bullet point using a hybrid approach.
        Returns (improved_text, was_ai_used)
        """
        # 1. Normalization
        cleaned = text.strip()
        if not cleaned: return text, False
        
        # 2. Rule-Based Fixes (Cosmetic)
        # If the only difference is casing or punctuation, we might want to skip AI
        # unless it's extremely short/weak.
        fixed_cosmetic = cleaned[0].upper() + cleaned[1:]
        if not fixed_cosmetic.endswith('.'): fixed_cosmetic += '.'
        
        if cleaned.lower() == text.lower().strip().rstrip('.'):
             # If it's already "decent" or we just want to save cost on simple edits
             if len(cleaned) > 20 or (cleaned.split()[0].lower() in HybridEnhancementService.STRONG_VERBS):
                 logger.info("Progressive Enhancement: Applied cosmetic fix without AI.")
                 return fixed_cosmetic, False

        # 3. Heuristic Strength Check
        has_metric = bool(re.search(r'\d+%|\$\d+|\b\d+\s+(?:users|clients|percent|hours)\b', cleaned))
        starts_with_strong_verb = cleaned.split()[0].lower() in HybridEnhancementService.STRONG_VERBS
        is_strong = has_metric and starts_with_strong_verb and len(cleaned) > 30

        # 4. Progressive Path
        if is_strong:
            # If already strong, just apply cosmetic polish and return
            fixed = cleaned[0].upper() + cleaned[1:]
            if not fixed.endswith('.'): fixed += '.'
            logger.info("Progressive Enhancement: Bullet already strong. Applying polish only.")
            return fixed, False

        # 4. AI Enhancement (Reasoning Required for weak bullets)
        logger.info("Progressive Enhancement: Weak content detected. Triggering AI reasoning.")
        
        from app.services.prompt_registry import PromptRegistryService
        prompt_obj = PromptRegistryService.get_prompt('resume_improvement')
        user_prompt = PromptRegistryService.format_prompt(
            prompt_obj,
            text=text,
            context=context
        )
        
        try:
            metered_resp = await AIMeteringService.ask_ai_metered(
                user_id=user_id,
                feature_type='resume_optimization', # feature_type mapping
                prompt=user_prompt,
                system_prompt=prompt_obj.system_prompt,
                temperature=0.3
            )
            
            if not metered_resp.get('success'):
                # Treat as failure, fallback to rules
                logger.warning(f"Metered AI Enhancement failed: {metered_resp.get('message')}")
                fixed = cleaned[0].upper() + cleaned[1:]
                if not fixed.endswith('.'): fixed += '.'
                return fixed, False

            ai_response = metered_resp.get('text', text)
            
            # 4. Failure Detection & Fallback
            from app.services.failure_monitor import AIFailureMonitor
            final_text = AIFailureMonitor.apply_safe_fallback(text, ai_response.strip())
            
            # If fallback returned something identical to original (except polish)
            # but AI text was different, it means we suppressed a failure.
            was_really_used = (final_text != text) and (final_text == ai_response.strip())
            
            return final_text, was_really_used
        except Exception as e:
            logger.error(f"AI Enhancement failed: {str(e)}")
            # Fallback to cosmetic polish
            fixed = cleaned[0].upper() + cleaned[1:]
            if not fixed.endswith('.'): fixed += '.'
            return fixed, False

    @staticmethod
    def analyze_coherence_fast(experience_data):
        """
        Fast rule-based check for timeline coherence.
        If serious gaps/overlaps are found, we return them without needing AI.
        """
        # This mirrors ExperienceValidatorService logic but focuses on speed
        # Logic is already in ExperienceValidatorService, so we leverage that
        from app.services.experience_validator import ExperienceValidatorService
        return ExperienceValidatorService.validate_experience(experience_data)
