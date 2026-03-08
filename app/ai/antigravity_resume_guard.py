import json
import logging
import re

logger = logging.getLogger(__name__)

class ResumeGuardViolation(Exception):
    """Raised when an AI-generated resume violates integrity or safety rules."""
    pass

class AntigravityResumeGuard:
    """
    Antigravity Guard for Resume Integrity.
    Prevents AI from hallucinating companies, inflating skills, or over-optimizing (keyword stuffing).
    """
    
    REQUIRED_SECTIONS = ["header", "summary", "skills", "experience", "education"]
    MAX_BULLET_LENGTH = 300  # Max characters per achievement bullet
    KEYWORD_DENSITY_THRESHOLD = 0.15 # Max 15% density for any single keyword
    
    @staticmethod
    def validate_resume_structure(data):
        """Validates the basic JSON structure."""
        if not isinstance(data, dict):
            raise ResumeGuardViolation("Invalid resume format: Not a dictionary.")
            
        for section in AntigravityResumeGuard.REQUIRED_SECTIONS:
            if section not in data:
                raise ResumeGuardViolation(f"Structural integrity failed: Missing section '{section}'.")
        
        return True

    @staticmethod
    def verify_factual_integrity(generated_json, original_profile):
        """
        Hard-enforcement of factual records.
        Ensures AI hasn't added new companies, skills, or fake durations.
        """
        # 1. Company Verification
        original_companies = {exp.get('company').lower() for exp in original_profile.get('experience', []) if exp.get('company')}
        generated_companies = {exp.get('company').lower() for exp in generated_json.get('experience', []) if exp.get('company')}
        
        new_companies = generated_companies - original_companies
        if new_companies:
            raise ResumeGuardViolation(f"Factual Violation: Hallucinated companies detected: {', '.join(new_companies)}")

        # 2. Skill Inflation Check
        # Convert original skills to a normalized set
        profile_skills_raw = original_profile.get('skills', [])
        if isinstance(profile_skills_raw, str):
            profile_skills = {s.strip().lower() for s in profile_skills_raw.split(',') if s.strip()}
        else:
            profile_skills = {s.lower() for s in profile_skills_raw if s}

        generated_skills = {s.lower() for s in generated_json.get('skills', [])}
        
        # We allow semantic variations, but "new" hard skills are blocked
        # This is a strict check. If the user wants to allow "AI-suggested" skills, this would be a warning.
        # Per requirements: "No skill inflation" -> Hard Block.
        inflated_skills = generated_skills - profile_skills
        if inflated_skills:
             # Logic to filter out common stop words or generic terms could go here
             # For now, we block any skill not in the profile.
             raise ResumeGuardViolation(f"Integrity Violation: Detected skill inflation: {', '.join(inflated_skills)}")

        # 3. Bullet Length Enforcement
        for exp in generated_json.get('experience', []):
            for bullet in exp.get('achievements', []):
                if len(bullet) > AntigravityResumeGuard.MAX_BULLET_LENGTH:
                    raise ResumeGuardViolation(f"Formatting Violation: Achievement bullet exceeds {AntigravityResumeGuard.MAX_BULLET_LENGTH} chars.")

        # 4. Keyword Density Check (Keyword Stuffing Protection)
        text_corpus = " ".join([
            generated_json.get('summary', ''),
            " ".join(generated_json.get('skills', [])),
            " ".join([a for exp in generated_json.get('experience', []) for a in exp.get('achievements', [])])
        ]).lower()
        
        words = re.findall(r'\w+', text_corpus)
        total_words = len(words)
        
        if total_words > 0:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            for word, count in word_counts.items():
                if len(word) > 3: # Ignore short words like 'the', 'and'
                    density = count / total_words
                    if density > AntigravityResumeGuard.KEYWORD_DENSITY_THRESHOLD:
                        raise ResumeGuardViolation(f"Safety Violation: Keyword stuffing detected for '{word}' ({density:.1%}).")

        return True

    @staticmethod
    def sanitize_content(content):
        """Removes unwanted AI artifacts."""
        if isinstance(content, str):
            # Strip markdown
            content = re.sub(r'```json\n?|```', '', content).strip()
            # Remove thinking blocks
            if "<thinking>" in content:
                content = content.split("</thinking>")[-1].strip()
            return content
        elif isinstance(content, dict):
            return {k: AntigravityResumeGuard.sanitize_content(v) for k, v in content.items()}
        elif isinstance(content, list):
            return [AntigravityResumeGuard.sanitize_content(i) for i in content]
        return content
