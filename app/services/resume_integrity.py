import hashlib
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ResumeIntegrityService:
    """
    Provides verification and tamper-detection for resumes.
    Ensures authenticity of AI-generated content and tracks versions.
    """

    SECRET_SALT = "sista-ai-integrity-salt-2026" # In production, this should be an env var

    @staticmethod
    def sign_resume(resume_data, version_id=None):
        """
        Generates an integrity signature for the resume data.
        Returns the data with an attached '_integrity' metadata block.
        """
        # Remove existing signature if present to calculate clean hash
        clean_data = {k: v for k, v in resume_data.items() if k != '_integrity'}
        
        # Consistent JSON string for hashing
        payload = json.dumps(clean_data, sort_keys=True)
        signature = ResumeIntegrityService._generate_hash(payload)
        
        metadata = {
            "version_id": version_id or datetime.now().strftime("%Y%m%d%H%M%S"),
            "signature": signature,
            "signed_at": datetime.now().isoformat(),
            "origin": "CareerJet AI Resume Builder"
        }
        
        resume_data['_integrity'] = metadata
        return resume_data

    @staticmethod
    def verify_integrity(resume_data):
        """
        Verifies if the resume data matches its stored signature.
        Returns (is_valid, metadata_if_any)
        """
        metadata = resume_data.get('_integrity')
        if not metadata or 'signature' not in metadata:
            return False, {"error": "No integrity watermark found."}
            
        stored_signature = metadata['signature']
        
        # Calculate expected signature
        clean_data = {k: v for k, v in resume_data.items() if k != '_integrity'}
        payload = json.dumps(clean_data, sort_keys=True)
        expected_signature = ResumeIntegrityService._generate_hash(payload)
        
        if stored_signature == expected_signature:
            return True, metadata
        else:
            return False, {"error": "Tamper detected: Content does not match signature."}

    @staticmethod
    def _generate_hash(text):
        """Generates a secure HMAC-like hash."""
        hash_input = f"{text}{ResumeIntegrityService.SECRET_SALT}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
