from datetime import datetime
from app.extensions import db

class ResumeDecisionLog(db.Model):
    """
    Stores explainability logs for AI decisions made during resume generation/optimization.
    Helps users understand "why" the AI made specific changes.
    """
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    action_type = db.Column(db.String(50), nullable=False) # 'skill_added', 'bullet_rewritten', 'score_change', 'generation_logic'
    decision_summary = db.Column(db.Text, nullable=False)
    rationale = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Resume
    resume = db.relationship('Resume', backref=db.backref('decision_logs', lazy=True, cascade="all, delete-orphan"))
