from datetime import datetime
from app.extensions import db
import json

class ResumeVersion(db.Model):
    """
    Tracks job-specific optimizations and history.
    """
    __tablename__ = 'resume_versions'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id'), nullable=True, index=True)
    
    version_number = db.Column(db.Integer, nullable=False)
    content_json = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(255))
    
    # Metadata
    ats_score = db.Column(db.Integer, nullable=True)
    change_log = db.Column(db.String(255))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'version_number': self.version_number,
            'job_id': self.job_id,
            'ats_score': self.ats_score,
            'change_log': self.change_log,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def get_diff(self, other_version):
        """
        Simple diff support. Returns keys that changed.
        In a real app, use a proper diffing library.
        """
        import difflib
        
        try:
            current = json.loads(self.content_json)
            other = json.loads(other_version.content_json)
            
            # Simple top-level key comparison for now
            diff_report = []
            for key in set(current.keys()) | set(other.keys()):
                if current.get(key) != other.get(key):
                    diff_report.append(key)
            return diff_report
        except:
            return []
            
    def soft_delete(self):
        self.deleted_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
