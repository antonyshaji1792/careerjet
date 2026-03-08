"""
Resume Job Links and ATS Scores Models
Tracks resume-job relationships and ATS scoring
"""

from datetime import datetime
from app.extensions import db
from sqlalchemy import Index


class ResumeJobLink(db.Model):
    """
    Links resumes to specific jobs for tracking and optimization.
    Many-to-many relationship with additional metadata.
    """
    __tablename__ = 'resume_job_links'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id', ondelete='CASCADE'), nullable=False, index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('resume_versions.id', ondelete='SET NULL'), nullable=True)
    
    # Link metadata
    link_type = db.Column(db.String(50), default='applied')  # applied, optimized, viewed, saved
    match_score = db.Column(db.Float, nullable=True)  # 0-100
    
    # Application tracking
    application_id = db.Column(db.Integer, db.ForeignKey('application.id', ondelete='SET NULL'), nullable=True)
    application_status = db.Column(db.String(50))  # pending, submitted, viewed, interview, rejected, accepted
    
    # Timestamps
    linked_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    applied_at = db.Column(db.DateTime, nullable=True)
    viewed_at = db.Column(db.DateTime, nullable=True)
    responded_at = db.Column(db.DateTime, nullable=True)
    
    # Soft delete
    is_active = db.Column(db.Boolean, default=True)
    deleted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    resume = db.relationship('Resume', backref=db.backref('job_links', lazy='dynamic'))
    job = db.relationship('JobPost', backref=db.backref('resume_links', lazy='dynamic'))
    version = db.relationship('ResumeVersion', backref=db.backref('job_links', lazy='dynamic'))
    
    __table_args__ = (
        Index('idx_resume_job_unique', 'resume_id', 'job_id', unique=True),
        Index('idx_resume_job_status', 'resume_id', 'application_status'),
        Index('idx_job_resume_score', 'job_id', 'match_score'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'resume_id': self.resume_id,
            'job_id': self.job_id,
            'version_id': self.version_id,
            'link_type': self.link_type,
            'match_score': self.match_score,
            'application_status': self.application_status,
            'linked_at': self.linked_at.isoformat() if self.linked_at else None,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'viewed_at': self.viewed_at.isoformat() if self.viewed_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None
        }
    
    @staticmethod
    def link_resume_to_job(resume_id, job_id, link_type='viewed', match_score=None, version_id=None):
        """Create or update resume-job link"""
        link = ResumeJobLink.query.filter_by(
            resume_id=resume_id,
            job_id=job_id
        ).first()
        
        if link:
            link.link_type = link_type
            if match_score is not None:
                link.match_score = match_score
            if version_id is not None:
                link.version_id = version_id
        else:
            link = ResumeJobLink(
                resume_id=resume_id,
                job_id=job_id,
                link_type=link_type,
                match_score=match_score,
                version_id=version_id
            )
            db.session.add(link)
        
        db.session.commit()
        return link
    
    def mark_applied(self, application_id=None):
        """Mark resume as applied to job"""
        self.link_type = 'applied'
        self.application_status = 'submitted'
        self.applied_at = datetime.utcnow()
        if application_id:
            self.application_id = application_id
        db.session.commit()
    
    def mark_viewed(self):
        """Mark resume as viewed by employer"""
        self.application_status = 'viewed'
        self.viewed_at = datetime.utcnow()
        db.session.commit()
    
    def mark_responded(self, status='interview'):
        """Mark employer response"""
        self.application_status = status
        self.responded_at = datetime.utcnow()
        db.session.commit()


class ATSScore(db.Model):
    """
    Stores ATS (Applicant Tracking System) compatibility scores.
    Tracks scores over time and by job.
    """
    __tablename__ = 'ats_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('resume_versions.id', ondelete='SET NULL'), nullable=True, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id', ondelete='SET NULL'), nullable=True, index=True)
    
    # Overall score
    overall_score = db.Column(db.Integer, nullable=False)  # 0-100
    
    # Component scores
    formatting_score = db.Column(db.Integer)  # 0-100
    keywords_score = db.Column(db.Integer)  # 0-100
    structure_score = db.Column(db.Integer)  # 0-100
    readability_score = db.Column(db.Integer)  # 0-100
    experience_score = db.Column(db.Integer)  # 0-100
    education_score = db.Column(db.Integer)  # 0-100
    
    # Detailed analysis
    matched_keywords = db.Column(db.Text)  # JSON array
    missing_keywords = db.Column(db.Text)  # JSON array
    keyword_density = db.Column(db.Float)  # 0-1
    
    # Recommendations
    recommendations = db.Column(db.Text)  # JSON array of suggestions
    
    # Metadata
    score_version = db.Column(db.String(20), default='1.0')  # Algorithm version
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    resume = db.relationship('Resume', backref=db.backref('ats_scores', lazy='dynamic'))
    version = db.relationship('ResumeVersion', backref=db.backref('ats_scores', lazy='dynamic'))
    job = db.relationship('JobPost', backref=db.backref('ats_scores', lazy='dynamic'))
    
    __table_args__ = (
        Index('idx_ats_resume_job', 'resume_id', 'job_id'),
        Index('idx_ats_score_date', 'resume_id', 'calculated_at'),
    )
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'overall_score': self.overall_score,
            'breakdown': {
                'formatting': self.formatting_score,
                'keywords': self.keywords_score,
                'structure': self.structure_score,
                'readability': self.readability_score,
                'experience': self.experience_score,
                'education': self.education_score
            },
            'matched_keywords': json.loads(self.matched_keywords) if self.matched_keywords else [],
            'missing_keywords': json.loads(self.missing_keywords) if self.missing_keywords else [],
            'keyword_density': self.keyword_density,
            'recommendations': json.loads(self.recommendations) if self.recommendations else [],
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }
    
    @staticmethod
    def calculate_and_store(resume_id, job_id=None, version_id=None):
        """
        Calculate ATS score for resume (optionally against specific job).
        This is a simplified version - real implementation would use NLP.
        """
        from app.models.resume import Resume
        from app.models.jobs import JobPost
        import json
        
        resume = Resume.query.get(resume_id)
        if not resume:
            return None
        
        # Simple scoring logic (can be enhanced with ML)
        formatting_score = 95  # Assume good formatting
        structure_score = 90   # Assume good structure
        readability_score = 85  # Assume good readability
        
        # Keyword matching if job provided
        if job_id:
            job = JobPost.query.get(job_id)
            if job and job.description:
                # Simple keyword extraction (enhance with NLP)
                job_keywords = set(job.description.lower().split())
                resume_text = resume.content_json or ""
                resume_keywords = set(resume_text.lower().split())
                
                matched = job_keywords & resume_keywords
                missing = job_keywords - resume_keywords
                
                keywords_score = int((len(matched) / len(job_keywords)) * 100) if job_keywords else 50
                matched_keywords = json.dumps(list(matched)[:20])
                missing_keywords = json.dumps(list(missing)[:20])
                keyword_density = len(matched) / len(resume_keywords) if resume_keywords else 0
            else:
                keywords_score = 50
                matched_keywords = json.dumps([])
                missing_keywords = json.dumps([])
                keyword_density = 0
        else:
            keywords_score = 50
            matched_keywords = json.dumps([])
            missing_keywords = json.dumps([])
            keyword_density = 0
        
        # Calculate overall score (weighted average)
        overall_score = int(
            (formatting_score * 0.2) +
            (keywords_score * 0.3) +
            (structure_score * 0.2) +
            (readability_score * 0.15) +
            (85 * 0.15)  # Default experience/education score
        )
        
        # Generate recommendations
        recommendations = []
        if keywords_score < 70:
            recommendations.append("Add more job-specific keywords")
        if formatting_score < 80:
            recommendations.append("Improve resume formatting")
        if readability_score < 75:
            recommendations.append("Simplify language for better readability")
        
        # Store score
        score = ATSScore(
            resume_id=resume_id,
            version_id=version_id,
            job_id=job_id,
            overall_score=overall_score,
            formatting_score=formatting_score,
            keywords_score=keywords_score,
            structure_score=structure_score,
            readability_score=readability_score,
            experience_score=85,
            education_score=85,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            keyword_density=keyword_density,
            recommendations=json.dumps(recommendations)
        )
        
        db.session.add(score)
        db.session.commit()
        
        return score
    
    @staticmethod
    def get_latest_score(resume_id, job_id=None):
        """Get most recent ATS score for resume"""
        query = ATSScore.query.filter_by(resume_id=resume_id)
        
        if job_id:
            query = query.filter_by(job_id=job_id)
        
        return query.order_by(ATSScore.calculated_at.desc()).first()
