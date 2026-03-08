from datetime import datetime
from app.extensions import db
from sqlalchemy.orm import validates

class Resume(db.Model):
    """
    Base Resume model. Represents the master resume for a user.
    """
    __tablename__ = 'resumes'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    title = db.Column(db.String(100), default="My Resume")
    content_json = db.Column(db.Text) # Master content
    file_path = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True) # Soft delete / Active status
    is_primary = db.Column(db.Boolean, default=False)
    is_generated = db.Column(db.Boolean, default=False)
    prompt_version_id = db.Column(db.Integer, db.ForeignKey('prompt_versions.id'), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow) # For recency sorting
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    versions = db.relationship('ResumeVersion', backref='resume', lazy=True, cascade="all, delete-orphan")
    skills = db.relationship('ResumeSkill', backref='resume', lazy=True, cascade="all, delete-orphan")

    def to_dict(self, secure=True):
        """Secure serialization method."""
        data = {
            'id': self.id,
            'title': self.title,
            'is_primary': self.is_primary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if not secure:
            data['content_json'] = self.content_json
        return data

    @validates('is_primary')
    def validate_one_primary(self, key, value):
        if value:
            # Set all other resumes for this user to is_primary=False
            Resume.query.filter_by(user_id=self.user_id).update({Resume.is_primary: False})
        return value

    def soft_delete(self):
        self.is_active = False
        self.deleted_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

class ResumeOptimization(db.Model):
    __tablename__ = 'resume_optimizations'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id'))
    optimized_content = db.Column(db.Text)
    ats_score = db.Column(db.Integer)
    missing_keywords = db.Column(db.Text)
    suggestions = db.Column(db.Text)
    prompt_version_id = db.Column(db.Integer, db.ForeignKey('prompt_versions.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
