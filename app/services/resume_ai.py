import json
import logging
import hashlib
from datetime import datetime
from app.services.ai_metering_service import AIMeteringService
from app.models.config import AnswerCache
from app.extensions import db

logger = logging.getLogger(__name__)

class ResumeAIService:
    """
    Service for AI-driven resume generation and optimization.
    Enforces factual integrity and structural consistency.
    """
    
    SYSTEM_PROMPT = """You are a senior technical recruiter and resume expert.
CRITICAL RULES:
1. NEVER modify or hallucinate facts, dates, companies, or degrees.
2. ONLY improve language impact, clarity, and keyword alignment.
3. Output MUST be valid JSON and exactly match the requested schema.
4. No conversational text; return only the JSON block.
5. Focus on quantifiable achievements using the STAR method where appropriate.
"""

    def __init__(self, user_id, budget_tokens=2000):
        self.user_id = user_id
        self.budget_tokens = budget_tokens

    async def generate_response(self, prompt, cache_key_data=None, schema_check=None):
        """
        Orchestrates AI call with caching, budgeting, and validation.
        """
        # 1. Check Cache
        cache_key = self._generate_cache_key(cache_key_data) if cache_key_data else None
        if cache_key:
            cached = self._get_cached_answer(cache_key)
            if cached:
                logger.debug(f"AI Cache Hit for {cache_key}")
                return cached

        # 2. Call AI with Metering
        try:
            metered_resp = await AIMeteringService.ask_ai_metered(
                user_id=self.user_id,
                feature_type='resume_optimization',
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=self.budget_tokens,
                temperature=0.3 # Lower temperature for consistency
            )
            
            if not metered_resp.get('success'):
                logger.error(f"Metered AI Resume Service Error: {metered_resp.get('message')}")
                return None

            raw_response = metered_resp.get('text', '')
            
            # 3. Parse & Validate
            cleaned_json = self._parse_and_clean_json(raw_response)
            
            if schema_check and cleaned_json:
                if not all(key in cleaned_json for key in schema_check):
                    logger.error(f"AI response missing required keys: {schema_check}")
                    return None

            # 4. Cache successful response
            if cache_key and cleaned_json:
                self._save_to_cache(cache_key, cleaned_json, prompt)
                
            return cleaned_json

        except Exception as e:
            logger.error(f"AI Resume Service Error: {str(e)}")
            return None

    def _generate_cache_key(self, data):
        """Generates a unique MD5 hash for the request data."""
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.md5(serialized.encode()).hexdigest()

    def _get_cached_answer(self, cache_key):
        """Retrieves answer from AnswerCache model."""
        cache_entry = AnswerCache.query.filter_by(
            user_id=self.user_id,
            question_text=f"AI_RESUME_V2_{cache_key}"
        ).first()
        
        if cache_entry:
            try:
                return json.loads(cache_entry.answer_text)
            except:
                return None
        return None

    def _save_to_cache(self, cache_key, data, original_prompt):
        """Persists AI response to database cache."""
        try:
            # Check if exists to update last_used_at
            entry = AnswerCache.query.filter_by(
                user_id=self.user_id,
                question_text=f"AI_RESUME_V2_{cache_key}"
            ).first()
            
            if entry:
                entry.last_used_at = datetime.utcnow()
            else:
                entry = AnswerCache(
                    user_id=self.user_id,
                    question_text=f"AI_RESUME_V2_{cache_key}",
                    answer_text=json.dumps(data)
                )
                db.session.add(entry)
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Failed to cache AI response: {str(e)}")

    def _parse_and_clean_json(self, text):
        """Extracts and parses JSON from AI response, handling markdown blocks."""
        if not text:
            return None
            
        try:
            # Strip markdown code blocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            return json.loads(text.strip())
        except (ValueError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse AI JSON: {str(e)} | Raw: {text[:200]}")
            return None
