import re
import logging
from app.services.llm_service import ask_ai

logger = logging.getLogger(__name__)

class AIFailureMonitor:
    """
    Monitors AI outputs for failures, hallucinations, and low-confidence results.
    Implements automated fallback to safe logic.
    """

    @staticmethod
    def calculate_confidence(original_text, ai_text):
        """
        Calculates a confidence score (0.0 to 1.0) based on output characteristics.
        """
        if not ai_text:
            return 0.0

        score = 1.0

        # 1. Length outlier check (Too short or excessively long vs original)
        len_orig = len(original_text)
        len_ai = len(ai_text)
        if len_orig > 0:
            ratio = len_ai / len_orig
            if ratio < 0.3 or ratio > 3.0:
                score -= 0.3
        
        # 2. Hallucination Check (Placeholder detection)
        placeholders = [r'\[.*?\]', r'\{.*?\}', r'<.*?>', r'INSERT_.*?']
        for p in placeholders:
            if re.search(p, ai_text):
                score -= 0.6 # Increased from 0.5 to ensure it drops below 0.5 threshold
                logger.warning(f"Failure Monitor: Potential placeholder/hallucination detected: {ai_text}")

        # 3. Repetition Check
        words = ai_text.lower().split()
        if len(words) > 10:
             unique_ratio = len(set(words)) / len(words)
             if unique_ratio < 0.4: # Very repetitive
                 score -= 0.4

        # 4. Refusal Check (AI says "I cannot", "As an AI")
        refusal_phrases = ["as an ai", "i cannot", "i am unable", "i'm sorry"]
        if any(phrase in ai_text.lower() for phrase in refusal_phrases):
            score = 0.0

        return max(0.0, score)

    @staticmethod
    def is_hallucinated(ai_text, context_data=None):
        """
        Heuristic to detect if AI added facts not present in context.
        context_data could be a list of known facts/keywords.
        """
        # Detection of frequent hallucination patterns in resumes
        patterns = [
            r'\[Your Name\]', r'123 Main St', r'phone_number_here',
            r'lorem ipsum', r'john doe', r'jane smith'
        ]
        for p in patterns:
            if re.search(p, ai_text, re.I):
                return True
        return False

    @staticmethod
    def apply_safe_fallback(original_text, ai_text, confidence_threshold=0.5):
        """
        Returns original text if AI confidence is low, otherwise returns AI text.
        """
        confidence = AIFailureMonitor.calculate_confidence(original_text, ai_text)
        
        if confidence < confidence_threshold or AIFailureMonitor.is_hallucinated(ai_text):
            logger.info(f"Failure Monitor: Low confidence ({confidence:.2f}). Triggering safe fallback.")
            
            # Simple rule-based polish as fallback
            cleaned = original_text.strip()
            if not cleaned: return original_text
            
            fixed = cleaned[0].upper() + cleaned[1:]
            if not fixed.endswith('.'): fixed += '.'
            return fixed
            
        return ai_text
