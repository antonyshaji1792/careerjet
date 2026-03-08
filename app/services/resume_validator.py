from app.ai.antigravity_resume_guard import AntigravityResumeGuard, ResumeGuardViolation
import logging

logger = logging.getLogger(__name__)

class ResumeValidatorService:
    """Service to validate resumes against security, factual integrity, and formatting rules."""
    
    def __init__(self):
        self.guard = AntigravityResumeGuard()

    def validate_all(self, resume_data, original_profile=None):
        """
        Runs full suite of validations: structure, factual integrity, and formatting.
        Raises ResumeGuardViolation on failure.
        """
        try:
            # 1. Structural Check
            self.guard.validate_resume_structure(resume_data)
            
            # 2. Factual and Content Check
            if original_profile:
                self.guard.verify_factual_integrity(resume_data, original_profile)
                
            return True, "All checks passed."
        except ResumeGuardViolation as e:
            logger.warning(f"Resume Guard Violation: {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Unexpected validation error: {str(e)}")
            return False, "An internal error occurred during validation."

    def sanitize(self, resume_data):
        return self.guard.sanitize_content(resume_data)
