import re
import logging

logger = logging.getLogger(__name__)

class InlineEditService:
    """
    Provides real-time validation for manual resume edits.
    Enforces ATS-friendly rules and warns users about potentially harmful changes.
    """

    ATS_RULES = {
        'max_bullet_length': 200,
        'min_bullet_length': 30,
        'prohibited_patterns': [
            (r'\(.*?\)', "Avoid excessive parentheses; some ATS systems struggle with nested structures."),
            (r'[^\x00-\x7F]+', "Non-ASCII characters detected. Use standard characters to ensure ATS readability."),
            (r'https?://\S+', "Hyperlinks in bullets can sometimes cause parsing issues. Link in header instead.")
        ]
    }

    @staticmethod
    def validate_content(field_path, value, context=None):
        """
        Validates a specific field's value against ATS best practices.
        Returns a list of warnings.
        """
        warnings = []
        
        if not value or not isinstance(value, str):
            return warnings

        # 1. Length Checks
        if 'experience' in field_path and 'achievements' in field_path:
            if len(value) > InlineEditService.ATS_RULES['max_bullet_length']:
                warnings.append({
                    'type': 'length_warning',
                    'message': f"Bullet is quite long ({len(value)} chars). Recruiters prefer concise 1-2 line bullets.",
                    'severity': 'warning'
                })
            elif len(value) < InlineEditService.ATS_RULES['min_bullet_length'] and len(value) > 0:
                warnings.append({
                    'type': 'brevity_warning',
                    'message': "This bullet might be too brief to demonstrate impact.",
                    'severity': 'info'
                })

        # 2. Pattern-based Warnings
        for pattern, msg in InlineEditService.ATS_RULES['prohibited_patterns']:
            if re.search(pattern, value):
                warnings.append({
                    'type': 'format_warning',
                    'message': msg,
                    'severity': 'warning'
                })

        # 3. Keyword Preservation (if context provided)
        if context and 'required_keywords' in context:
            missing = [kw for kw in context['required_keywords'] if kw.lower() not in value.lower()]
            if missing and len(missing) > 0:
                 # Only warn if it's a major keyword and field is summary or similar
                 warnings.append({
                     'type': 'keyword_warning',
                     'message': f"Removing key terms like '{missing[0]}' may lower your ATS match score.",
                     'severity': 'warning'
                 })

        return warnings

    @staticmethod
    def get_ats_health_score(resume_json):
        """
        Calculates an overall 'ATS Friendliness' score based on structural rules.
        """
        penalty = 0
        total_checks = 0
        
        # Check experience structure
        exp = resume_json.get('experience', [])
        for job in exp:
            achievements = job.get('achievements', [])
            total_checks += len(achievements)
            for bullet in achievements:
                if len(bullet) > 200: penalty += 5
                if len(bullet) < 30: penalty += 2
        
        score = max(0, 100 - penalty)
        return score
