"""
Resume Metrics and Tagging Models
Enhanced tracking and organization
"""

from datetime import datetime
from app.extensions import db
from sqlalchemy import Index


class ResumeMetrics(db.Model):
    """
    Comprehensive metrics tracking for resume performance.
    Tracks views, applications, interviews, and success rates.
    """
    __tablename__ = 'resume_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    version_id = db.Column(db.Integer, db.ForeignKey('resume_versions.id', ondelete='SET NULL'), nullable=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id', ondelete='SET NULL'), nullable=True)
    
    # View metrics
    views = db.Column(db.Integer, default=0)
    unique_views = db.Column(db.Integer, default=0)
    downloads = db.Column(db.Integer, default=0)
    
    # Application metrics
    applications_sent = db.Column(db.Integer, default=0)
    applications_viewed = db.Column(db.Integer, default=0)
    applications_rejected = db.Column(db.Integer, default=0)
    
    # Interview metrics
    phone_screens = db.Column(db.Integer, default=0)
    interviews_scheduled = db.Column(db.Integer, default=0)
    interviews_completed = db.Column(db.Integer, default=0)
    offers_received = db.Column(db.Integer, default=0)
    
    # Success rates (calculated fields)
    view_to_apply_rate = db.Column(db.Float, default=0.0)  # %
    apply_to_interview_rate = db.Column(db.Float, default=0.0)  # %
    interview_to_offer_rate = db.Column(db.Float, default=0.0)  # %
    
    # Time tracking
    avg_response_time_hours = db.Column(db.Float, nullable=True)
    first_view_at = db.Column(db.DateTime, nullable=True)
    last_view_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resume = db.relationship('Resume', backref=db.backref('metrics', lazy='dynamic'))
    version = db.relationship('ResumeVersion', backref=db.backref('metrics', lazy='dynamic'))
    job = db.relationship('JobPost', backref=db.backref('resume_metrics', lazy='dynamic'))
    
    __table_args__ = (
        Index('idx_metrics_resume_job', 'resume_id', 'job_id'),
        Index('idx_metrics_updated', 'updated_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'resume_id': self.resume_id,
            'job_id': self.job_id,
            'views': {
                'total': self.views,
                'unique': self.unique_views,
                'downloads': self.downloads
            },
            'applications': {
                'sent': self.applications_sent,
                'viewed': self.applications_viewed,
                'rejected': self.applications_rejected
            },
            'interviews': {
                'phone_screens': self.phone_screens,
                'scheduled': self.interviews_scheduled,
                'completed': self.interviews_completed,
                'offers': self.offers_received
            },
            'success_rates': {
                'view_to_apply': self.view_to_apply_rate,
                'apply_to_interview': self.apply_to_interview_rate,
                'interview_to_offer': self.interview_to_offer_rate
            },
            'avg_response_time_hours': self.avg_response_time_hours,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def increment_metric(self, metric_name):
        """Increment a specific metric"""
        if hasattr(self, metric_name):
            current = getattr(self, metric_name) or 0
            setattr(self, metric_name, current + 1)
            self.recalculate_rates()
            self.updated_at = datetime.utcnow()
            db.session.commit()
    
    def recalculate_rates(self):
        """Recalculate success rates"""
        # View to apply rate
        if self.views > 0:
            self.view_to_apply_rate = (self.applications_sent / self.views) * 100
        
        # Apply to interview rate
        if self.applications_sent > 0:
            self.apply_to_interview_rate = (self.interviews_scheduled / self.applications_sent) * 100
        
        # Interview to offer rate
        if self.interviews_completed > 0:
            self.interview_to_offer_rate = (self.offers_received / self.interviews_completed) * 100
    
    @staticmethod
    def get_or_create(resume_id, job_id=None, version_id=None):
        """Get existing metrics or create new"""
        metrics = ResumeMetrics.query.filter_by(
            resume_id=resume_id,
            job_id=job_id
        ).first()
        
        if not metrics:
            metrics = ResumeMetrics(
                resume_id=resume_id,
                job_id=job_id,
                version_id=version_id
            )
            db.session.add(metrics)
            db.session.commit()
        
        return metrics
    
    @staticmethod
    def get_aggregate_stats(resume_id):
        """Get aggregated statistics across all jobs"""
        stats = db.session.query(
            db.func.sum(ResumeMetrics.views).label('total_views'),
            db.func.sum(ResumeMetrics.applications_sent).label('total_applications'),
            db.func.sum(ResumeMetrics.interviews_scheduled).label('total_interviews'),
            db.func.sum(ResumeMetrics.offers_received).label('total_offers'),
            db.func.avg(ResumeMetrics.apply_to_interview_rate).label('avg_interview_rate')
        ).filter(ResumeMetrics.resume_id == resume_id).first()
        
        return {
            'total_views': stats.total_views or 0,
            'total_applications': stats.total_applications or 0,
            'total_interviews': stats.total_interviews or 0,
            'total_offers': stats.total_offers or 0,
            'avg_interview_rate': round(stats.avg_interview_rate or 0, 2)
        }


class ResumeTag(db.Model):
    """
    Tags for organizing and categorizing resumes.
    Supports custom user tags and system tags.
    """
    __tablename__ = 'resume_tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, index=True)
    slug = db.Column(db.String(50), nullable=False, index=True)
    
    # Tag metadata
    tag_type = db.Column(db.String(20), default='custom')  # custom, system, industry, role, skill
    color = db.Column(db.String(7), default='#3b82f6')  # Hex color code
    icon = db.Column(db.String(50))  # Font Awesome icon class
    
    # User association
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=True, index=True)
    is_public = db.Column(db.Boolean, default=False)  # Public/shared tags
    
    # Usage tracking
    usage_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('resume_tags', lazy='dynamic'))
    
    __table_args__ = (
        Index('idx_tag_user_slug', 'user_id', 'slug', unique=True),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'tag_type': self.tag_type,
            'color': self.color,
            'icon': self.icon,
            'usage_count': self.usage_count
        }
    
    @staticmethod
    def create_or_get(name, user_id, tag_type='custom', color='#3b82f6'):
        """Create tag or get existing"""
        import re
        slug = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))
        
        tag = ResumeTag.query.filter_by(user_id=user_id, slug=slug).first()
        
        if not tag:
            tag = ResumeTag(
                name=name,
                slug=slug,
                user_id=user_id,
                tag_type=tag_type,
                color=color
            )
            db.session.add(tag)
            db.session.commit()
        
        return tag


class ResumeTagAssociation(db.Model):
    """
    Association table for resume-tag many-to-many relationship.
    """
    __tablename__ = 'resume_tag_associations'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    tag_id = db.Column(db.Integer, db.ForeignKey('resume_tags.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Association metadata
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    resume = db.relationship('Resume', backref=db.backref('tag_associations', lazy='dynamic', cascade='all, delete-orphan'))
    tag = db.relationship('ResumeTag', backref=db.backref('resume_associations', lazy='dynamic'))
    
    __table_args__ = (
        Index('idx_resume_tag_unique', 'resume_id', 'tag_id', unique=True),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'resume_id': self.resume_id,
            'tag': self.tag.to_dict() if self.tag else None,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }
    
    @staticmethod
    def add_tag_to_resume(resume_id, tag_id, user_id=None):
        """Add tag to resume"""
        existing = ResumeTagAssociation.query.filter_by(
            resume_id=resume_id,
            tag_id=tag_id
        ).first()
        
        if existing:
            return existing
        
        association = ResumeTagAssociation(
            resume_id=resume_id,
            tag_id=tag_id,
            added_by=user_id
        )
        db.session.add(association)
        
        # Increment tag usage count
        tag = ResumeTag.query.get(tag_id)
        if tag:
            tag.usage_count += 1
        
        db.session.commit()
        return association
    
    @staticmethod
    def remove_tag_from_resume(resume_id, tag_id):
        """Remove tag from resume"""
        association = ResumeTagAssociation.query.filter_by(
            resume_id=resume_id,
            tag_id=tag_id
        ).first()
        
        if association:
            # Decrement tag usage count
            tag = ResumeTag.query.get(tag_id)
            if tag and tag.usage_count > 0:
                tag.usage_count -= 1
            
            db.session.delete(association)
            db.session.commit()
            return True
        
        return False
    
    @staticmethod
    def get_resume_tags(resume_id):
        """Get all tags for a resume"""
        associations = ResumeTagAssociation.query.filter_by(resume_id=resume_id).all()
        return [assoc.tag for assoc in associations if assoc.tag]


class ResumeActivityLog(db.Model):
    """
    Activity log for resume actions.
    Tracks all changes and interactions for audit trail.
    """
    __tablename__ = 'resume_activity_log'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    
    # Activity details
    action = db.Column(db.String(50), nullable=False, index=True)  # created, updated, viewed, downloaded, optimized, deleted
    action_details = db.Column(db.Text)  # JSON with additional details
    
    # Context
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    user_agent = db.Column(db.String(500))
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    resume = db.relationship('Resume', backref=db.backref('activity_log', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('resume_activities', lazy='dynamic'))
    
    __table_args__ = (
        Index('idx_activity_resume_action', 'resume_id', 'action'),
        Index('idx_activity_user_date', 'user_id', 'created_at'),
    )
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'action': self.action,
            'details': json.loads(self.action_details) if self.action_details else {},
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def log_activity(resume_id, action, user_id=None, details=None, ip_address=None, user_agent=None):
        """Log resume activity"""
        import json
        
        log = ResumeActivityLog(
            resume_id=resume_id,
            user_id=user_id,
            action=action,
            action_details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(log)
        db.session.commit()
        return log
    
    @staticmethod
    def get_recent_activity(resume_id, limit=10):
        """Get recent activity for resume"""
        return ResumeActivityLog.query.filter_by(
            resume_id=resume_id
        ).order_by(
            ResumeActivityLog.created_at.desc()
        ).limit(limit).all()
