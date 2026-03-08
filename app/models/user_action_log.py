from datetime import datetime
from app.extensions import db

class UserActionLog(db.Model):
    """
    Tracks user feedback on AI actions (e.g., rejections, manual overrides).
    Used to improve AI failure detection and model alignment.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=True)
    action_type = db.Column(db.String(50), nullable=False) # 'ai_rejected', 'manual_fix', 'undo'
    original_ai_text = db.Column(db.Text)
    final_user_text = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
