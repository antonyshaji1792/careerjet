"""
Resume Sections Models - Granular storage for resume components
Allows individual section management and versioning
"""

from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Index


class ResumeSection(db.Model):
    """
    Base model for all resume sections.
    Stores individual sections separately for granular control.
    """
    __tablename__ = 'resume_sections'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('resume_versions.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Section metadata
    section_type = db.Column(db.String(50), nullable=False, index=True)  # summary, experience, education, skills, projects, certifications
    section_order = db.Column(db.Integer, default=0)  # Display order
    
    # Content (flexible JSON storage for different section types)
    content = db.Column(db.Text, nullable=False)  # JSON string
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_ai_generated = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    resume = db.relationship('Resume', backref=db.backref('sections', lazy='dynamic'))
    version = db.relationship('ResumeVersion', backref=db.backref('sections', lazy='dynamic'))
    
    __table_args__ = (
        Index('idx_resume_section_type', 'resume_id', 'section_type'),
        Index('idx_resume_section_active', 'resume_id', 'is_active'),
    )
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'section_type': self.section_type,
            'section_order': self.section_order,
            'content': json.loads(self.content) if self.content else {},
            'is_active': self.is_active,
            'is_ai_generated': self.is_ai_generated,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def soft_delete(self):
        """Soft delete the section"""
        self.is_active = False
        self.deleted_at = datetime.utcnow()
        db.session.commit()


class ResumeSummary(db.Model):
    """Professional summary/objective section"""
    __tablename__ = 'resume_summaries'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('resume_versions.id', ondelete='SET NULL'), nullable=True)
    
    summary_text = db.Column(db.Text, nullable=False)
    tone = db.Column(db.String(50))  # professional, confident, creative, minimalist
    word_count = db.Column(db.Integer)
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'summary_text': self.summary_text,
            'tone': self.tone,
            'word_count': self.word_count,
            'is_active': self.is_active
        }


class ResumeExperience(db.Model):
    """Work experience entries"""
    __tablename__ = 'resume_experiences'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('resume_versions.id', ondelete='SET NULL'), nullable=True)
    
    # Company details
    company_name = db.Column(db.String(200), nullable=False, index=True)
    job_title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200))
    
    # Dates
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date, nullable=True)
    is_current = db.Column(db.Boolean, default=False)
    
    # Content
    description = db.Column(db.Text)
    achievements = db.Column(db.Text)  # JSON array of achievement bullets
    
    # Metadata
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)  # Verified via LinkedIn/other source
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_experience_company', 'resume_id', 'company_name'),
        Index('idx_experience_dates', 'start_date', 'end_date'),
    )
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'company_name': self.company_name,
            'job_title': self.job_title,
            'location': self.location,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'is_current': self.is_current,
            'description': self.description,
            'achievements': json.loads(self.achievements) if self.achievements else [],
            'is_verified': self.is_verified
        }


class ResumeEducation(db.Model):
    """Education entries"""
    __tablename__ = 'resume_education'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('resume_versions.id', ondelete='SET NULL'), nullable=True)
    
    institution_name = db.Column(db.String(200), nullable=False)
    degree = db.Column(db.String(200), nullable=False)
    field_of_study = db.Column(db.String(200))
    
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date, nullable=True)
    is_current = db.Column(db.Boolean, default=False)
    
    gpa = db.Column(db.Float, nullable=True)
    honors = db.Column(db.String(200))
    activities = db.Column(db.Text)
    
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'institution_name': self.institution_name,
            'degree': self.degree,
            'field_of_study': self.field_of_study,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'gpa': self.gpa,
            'honors': self.honors
        }


class ResumeProject(db.Model):
    """Projects section"""
    __tablename__ = 'resume_projects'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('resume_versions.id', ondelete='SET NULL'), nullable=True)
    
    project_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    technologies = db.Column(db.Text)  # JSON array
    url = db.Column(db.String(500))
    github_url = db.Column(db.String(500))
    
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date, nullable=True)
    
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'project_name': self.project_name,
            'description': self.description,
            'technologies': json.loads(self.technologies) if self.technologies else [],
            'url': self.url,
            'github_url': self.github_url
        }


class ResumeCertification(db.Model):
    """Certifications and licenses"""
    __tablename__ = 'resume_certifications'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('resume_versions.id', ondelete='SET NULL'), nullable=True)
    
    certification_name = db.Column(db.String(200), nullable=False)
    issuing_organization = db.Column(db.String(200))
    issue_date = db.Column(db.Date)
    expiration_date = db.Column(db.Date, nullable=True)
    credential_id = db.Column(db.String(100))
    credential_url = db.Column(db.String(500))
    
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'certification_name': self.certification_name,
            'issuing_organization': self.issuing_organization,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'credential_url': self.credential_url
        }
