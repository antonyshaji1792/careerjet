from datetime import datetime
from app.extensions import db


class ResumeAnalytics(db.Model):
    """
    Tracks resume performance metrics and analytics.
    Helps users understand which resume versions perform best.
    """
    __tablename__ = 'resume_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id'), nullable=True, index=True)
    
    # Metrics
    views = db.Column(db.Integer, default=0)
    downloads = db.Column(db.Integer, default=0)
    applications = db.Column(db.Integer, default=0)
    responses = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resume = db.relationship('Resume', backref=db.backref('analytics', lazy='dynamic'))
    job = db.relationship('JobPost', backref=db.backref('resume_analytics', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'resume_id': self.resume_id,
            'job_id': self.job_id,
            'views': self.views,
            'downloads': self.downloads,
            'applications': self.applications,
            'responses': self.responses,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def increment_metric(resume_id, metric_name, job_id=None):
        """
        Increment a specific metric for a resume.
        Creates analytics record if it doesn't exist.
        """
        analytics = ResumeAnalytics.query.filter_by(
            resume_id=resume_id,
            job_id=job_id
        ).first()
        
        if not analytics:
            analytics = ResumeAnalytics(
                resume_id=resume_id,
                job_id=job_id
            )
            db.session.add(analytics)
        
        if hasattr(analytics, metric_name):
            current_value = getattr(analytics, metric_name)
            setattr(analytics, metric_name, current_value + 1)
            analytics.updated_at = datetime.utcnow()
            db.session.commit()
            return True
        
        return False
    
    @staticmethod
    def get_resume_stats(resume_id):
        """Get aggregated statistics for a resume across all jobs"""
        stats = db.session.query(
            db.func.sum(ResumeAnalytics.views).label('total_views'),
            db.func.sum(ResumeAnalytics.downloads).label('total_downloads'),
            db.func.sum(ResumeAnalytics.applications).label('total_applications'),
            db.func.sum(ResumeAnalytics.responses).label('total_responses')
        ).filter(ResumeAnalytics.resume_id == resume_id).first()
        
        return {
            'total_views': stats.total_views or 0,
            'total_downloads': stats.total_downloads or 0,
            'total_applications': stats.total_applications or 0,
            'total_responses': stats.total_responses or 0,
            'response_rate': (stats.total_responses / stats.total_applications * 100) 
                           if stats.total_applications and stats.total_applications > 0 else 0
        }


class ResumeUpload(db.Model):
    """
    Tracks resume file uploads for security and auditing.
    Helps identify upload issues and malicious files.
    """
    __tablename__ = 'resume_uploads'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # File metadata
    original_filename = db.Column(db.String(255))
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    
    # Upload status
    upload_status = db.Column(db.String(50), default='pending')  # pending, success, failed, virus_detected
    error_message = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('resume_uploads', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'upload_status': self.upload_status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def log_upload(user_id, filename, file_size, mime_type, status='success', error=None):
        """Log a resume upload attempt"""
        upload = ResumeUpload(
            user_id=user_id,
            original_filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            upload_status=status,
            error_message=error
        )
        db.session.add(upload)
        db.session.commit()
        return upload


class ResumeKeyword(db.Model):
    """
    Stores extracted keywords and their frequencies for ATS optimization.
    Helps track keyword coverage and optimization effectiveness.
    """
    __tablename__ = 'resume_keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id'), nullable=True, index=True)
    
    # Keyword data
    keyword = db.Column(db.String(100), nullable=False, index=True)
    frequency = db.Column(db.Integer, default=1)
    category = db.Column(db.String(50))  # skill, tool, technology, soft_skill, industry
    
    # Metadata
    is_matched = db.Column(db.Boolean, default=False)  # Matched with job description
    importance_score = db.Column(db.Float, default=0.0)  # 0-1 relevance score
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resume = db.relationship('Resume', backref=db.backref('keywords', lazy='dynamic'))
    job = db.relationship('JobPost', backref=db.backref('resume_keywords', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'keyword': self.keyword,
            'frequency': self.frequency,
            'category': self.category,
            'is_matched': self.is_matched,
            'importance_score': self.importance_score
        }
    
    @staticmethod
    def extract_and_store(resume_id, text, job_id=None):
        """
        Extract keywords from resume text and store them.
        Uses simple frequency-based extraction (can be enhanced with NLP).
        """
        import re
        from collections import Counter
        
        # Simple keyword extraction (can be enhanced with spaCy or NLTK)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Common stop words to exclude
        stop_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'has', 'had', 'was', 'were', 'been', 'being'}
        
        # Filter and count
        filtered_words = [w for w in words if w not in stop_words]
        word_counts = Counter(filtered_words)
        
        # Store top keywords
        for word, count in word_counts.most_common(50):
            keyword = ResumeKeyword.query.filter_by(
                resume_id=resume_id,
                keyword=word,
                job_id=job_id
            ).first()
            
            if keyword:
                keyword.frequency = count
            else:
                keyword = ResumeKeyword(
                    resume_id=resume_id,
                    job_id=job_id,
                    keyword=word,
                    frequency=count
                )
                db.session.add(keyword)
        
        db.session.commit()
        return True
