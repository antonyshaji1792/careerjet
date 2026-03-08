from datetime import datetime
from app.extensions import db

class AIUsageLog(db.Model):
    """
    Immutable logs of AI API calls and credit consumption.
    """
    __tablename__ = 'ai_usage_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    feature_type = db.Column(db.String(50), nullable=False) # e.g. 'resume_builder', 'interview_coach'
    ai_model = db.Column(db.String(100))
    credits_used = db.Column(db.Integer, default=0)
    tokens_used = db.Column(db.Integer, default=0)
    execution_time = db.Column(db.Float) # in seconds
    status = db.Column(db.String(20)) # success, failed
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship for convenience
    user = db.relationship('User', backref=db.backref('ai_usage_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<AIUsageLog {self.id} user={self.user_id} feature={self.feature_type}>'
