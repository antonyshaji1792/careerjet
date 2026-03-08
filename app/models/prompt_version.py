from datetime import datetime
from app.extensions import db

class PromptVersion(db.Model):
    """
    Production-grade AI Prompt Versioning.
    Tracks all AI prompts to ensures auditability, reproducibility, and security.
    """
    __tablename__ = 'prompt_versions'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    version = db.Column(db.String(50), nullable=False)
    
    # Prompt logic
    system_prompt = db.Column(db.Text)
    user_prompt_template = db.Column(db.Text, nullable=False)
    
    # Model parameters (Determinism Control)
    model = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float, default=0.0) # Standard for production determinism
    max_tokens = db.Column(db.Integer, default=1000)
    top_p = db.Column(db.Float, default=1.0)
    frequency_penalty = db.Column(db.Float, default=0.0)
    presence_penalty = db.Column(db.Float, default=0.0)
    stop_sequences = db.Column(db.String(255)) # Comma separated
    
    # Governance
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Metadata for explainability
    description = db.Column(db.String(255))
    change_log = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint('name', 'version', name='_name_version_uc'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }
