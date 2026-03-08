import re
import logging

logger = logging.getLogger(__name__)

class PIIService:
    """
    Handles detection and redaction of PII (Personally Identifiable Information)
    to support different privacy-preserving export modes.
    """

    GENDER_INDICATORS = [
        r'\bhe/him\b', r'\bshe/her\b', r'\bthey/them\b',
        r'\bhe\b', r'\bshe\b', r'\bthey\b', r'\bhim\b', r'\bher\b', r'\bthem\b',
        r'\bmale\b', r'\bfemale\b', r'\bgender\b'
    ]

    @staticmethod
    def redact_resume(resume_data, mode="full"):
        """
        Applies redaction rules to resume data based on the requested mode.
        Modes: 'full', 'recruiter-safe', 'public'
        """
        if mode == "full":
            return resume_data

        # Deep copy to avoid modifying original if passed by reference
        import copy
        redacted = copy.deepcopy(resume_data)
        header = redacted.get('header', {})

        if mode == "recruiter-safe":
            # Keep Name, Phone, Email.
            # Redact absolute address (usually keep City, State)
            if 'location' in header:
                header['location'] = PIIService._summarize_location(header['location'])
            
            # Redact DOB if exists
            if 'dob' in header:
                header['dob'] = "[REDACTED]"
            
            # Remove gender indicators from summary/experience
            redacted['summary'] = PIIService._redact_text(redacted.get('summary', ''))
            PIIService._redact_experience(redacted.get('experience', []))

        elif mode == "public":
            # Remove Phone, Email. 
            # Redact absolute address.
            if 'phone' in header: header['phone'] = "[REDACTED]"
            if 'email' in header: header['email'] = "[REDACTED]"
            if 'location' in header:
                header['location'] = PIIService._summarize_location(header['location'])
            
            if 'dob' in header: header['dob'] = "[REDACTED]"
            
            # Deep text redaction
            redacted['summary'] = PIIService._redact_text(redacted.get('summary', ''), extreme=True)
            PIIService._redact_experience(redacted.get('experience', []), extreme=True)

        return redacted

    @staticmethod
    def _summarize_location(location_str):
        """Redacts street address, leaves City, State/Country."""
        if not location_str: return ""
        # Very simple heuristic: take last 2 parts of a comma-separated string
        parts = [p.strip() for p in location_str.split(',')]
        if len(parts) >= 2:
            return ", ".join(parts[-2:])
        return location_str

    @staticmethod
    def _redact_text(text, extreme=False):
        """Removes gender indicators and optionally more via regex."""
        if not text: return ""
        
        # 1. Redact Gender
        for pattern in PIIService.GENDER_INDICATORS:
            text = re.sub(pattern, "[REDACTED]", text, flags=re.I)
            
        if extreme:
            # Redact email-like patterns
            text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[EMAIL REDACTED]", text)
            # Redact phone patterns
            text = re.sub(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', "[PHONE REDACTED]", text)
            
        return text

    @staticmethod
    def _redact_experience(experience_list, extreme=False):
        for exp in experience_list:
            if 'achievements' in exp:
                exp['achievements'] = [PIIService._redact_text(a, extreme) for a in exp['achievements']]
            if 'role' in exp:
                exp['role'] = PIIService._redact_text(exp['role'], extreme)
