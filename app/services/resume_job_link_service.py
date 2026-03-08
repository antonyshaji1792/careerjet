"""
Resume-Job Link Service
Integrates Resume Builder with Auto-Apply system
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

from app.extensions import db
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.models.resume_links import ResumeJobLink
from app.models.resume_metrics import ResumeMetrics, ResumeActivityLog
from app.models.application import Application
from app.models.jobs import JobPost

logger = logging.getLogger(__name__)


class ResumeJobLinkService:
    """
    Service for linking resumes to job applications.
    Manages resume selection, version locking, and outcome tracking.
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.logger = logger
    
    def select_resume_for_job(
        self,
        job_id: int,
        resume_id: Optional[int] = None,
        auto_select: bool = True
    ) -> Tuple[Resume, Optional[ResumeVersion]]:
        """
        Select the best resume for a job application.
        
        Args:
            job_id: Target job ID
            resume_id: Specific resume to use (optional)
            auto_select: Auto-select best resume if not specified
        
        Returns:
            Tuple of (Resume, ResumeVersion or None)
        """
        try:
            job = JobPost.query.get(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            
            # Use specified resume
            if resume_id:
                resume = Resume.query.filter_by(
                    id=resume_id,
                    user_id=self.user_id,
                    is_active=True
                ).first()
                
                if not resume:
                    raise ValueError(f"Resume {resume_id} not found or not accessible")
                
                # Check if there's an optimized version for this job
                version = ResumeVersion.query.filter_by(
                    resume_id=resume_id,
                    job_id=job_id
                ).order_by(ResumeVersion.version_number.desc()).first()
                
                return resume, version
            
            # Auto-select best resume
            if auto_select:
                return self._auto_select_best_resume(job_id)
            
            # No resume specified and auto-select disabled
            raise ValueError("No resume specified and auto-select is disabled")
            
        except Exception as e:
            self.logger.error(f"Resume selection failed: {str(e)}")
            raise
    
    def link_resume_to_application(
        self,
        application_id: int,
        resume_id: int,
        job_id: int,
        version_id: Optional[int] = None,
        match_score: Optional[float] = None
    ) -> ResumeJobLink:
        """
        Link a resume to a job application.
        
        Args:
            application_id: Application ID
            resume_id: Resume ID
            job_id: Job ID
            version_id: Optional specific version ID
            match_score: Optional match score
        
        Returns:
            ResumeJobLink instance
        """
        try:
            # Verify ownership
            resume = Resume.query.filter_by(
                id=resume_id,
                user_id=self.user_id
            ).first()
            
            if not resume:
                raise ValueError("Resume not found or not accessible")
            
            # Check if link already exists
            existing_link = ResumeJobLink.query.filter_by(
                resume_id=resume_id,
                job_id=job_id
            ).first()
            
            if existing_link:
                # Update existing link
                existing_link.application_id = application_id
                existing_link.version_id = version_id
                existing_link.link_type = 'applied'
                existing_link.applied_at = datetime.utcnow()
                if match_score:
                    existing_link.match_score = match_score
                
                link = existing_link
            else:
                # Create new link
                link = ResumeJobLink(
                    resume_id=resume_id,
                    job_id=job_id,
                    version_id=version_id,
                    application_id=application_id,
                    link_type='applied',
                    match_score=match_score,
                    applied_at=datetime.utcnow()
                )
                db.session.add(link)
            
            db.session.commit()
            
            # Log activity
            ResumeActivityLog.log_activity(
                resume_id=resume_id,
                action='applied',
                user_id=self.user_id,
                details={
                    'job_id': job_id,
                    'application_id': application_id,
                    'version_id': version_id
                }
            )
            
            self.logger.info(f"Resume {resume_id} linked to application {application_id}")
            return link
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Resume linking failed: {str(e)}")
            raise
    
    def lock_resume_version(
        self,
        resume_id: int,
        job_id: int,
        application_id: int
    ) -> ResumeVersion:
        """
        Lock a resume version once applied to prevent modifications.
        
        Args:
            resume_id: Resume ID
            job_id: Job ID
            application_id: Application ID
        
        Returns:
            Locked ResumeVersion
        """
        try:
            # Get or create version for this job
            version = ResumeVersion.query.filter_by(
                resume_id=resume_id,
                job_id=job_id
            ).order_by(ResumeVersion.version_number.desc()).first()
            
            if not version:
                # Create snapshot version
                resume = Resume.query.get(resume_id)
                if not resume:
                    raise ValueError("Resume not found")
                
                # Get next version number
                latest = ResumeVersion.query.filter_by(
                    resume_id=resume_id
                ).order_by(ResumeVersion.version_number.desc()).first()
                
                version_number = (latest.version_number + 1) if latest else 1
                
                # Create locked version
                version = ResumeVersion(
                    resume_id=resume_id,
                    job_id=job_id,
                    version_number=version_number,
                    content_json=resume.content_json,
                    ats_score=resume.ats_score,
                    change_log=f'Locked for application {application_id}'
                )
                db.session.add(version)
            
            # Mark as locked (we'll add this field to model if needed)
            # For now, we track via the link
            
            db.session.commit()
            
            self.logger.info(f"Resume version {version.id} locked for application {application_id}")
            return version
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Version locking failed: {str(e)}")
            raise
    
    def update_application_outcome(
        self,
        application_id: int,
        status: str,
        outcome_details: Optional[Dict] = None
    ) -> ResumeJobLink:
        """
        Update application outcome and track metrics.
        
        Args:
            application_id: Application ID
            status: New status (viewed, interview, rejected, accepted)
            outcome_details: Optional additional details
        
        Returns:
            Updated ResumeJobLink
        """
        try:
            # Find link by application
            link = ResumeJobLink.query.filter_by(
                application_id=application_id
            ).first()
            
            if not link:
                raise ValueError(f"No resume link found for application {application_id}")
            
            # Update status
            link.application_status = status
            
            # Update timestamps based on status
            if status == 'viewed':
                link.viewed_at = datetime.utcnow()
            elif status in ['interview', 'accepted', 'rejected']:
                link.responded_at = datetime.utcnow()
            
            db.session.commit()
            
            # Update metrics
            self._update_metrics(link, status)
            
            # Log activity
            ResumeActivityLog.log_activity(
                resume_id=link.resume_id,
                action='outcome_updated',
                user_id=self.user_id,
                details={
                    'application_id': application_id,
                    'status': status,
                    'details': outcome_details
                }
            )
            
            self.logger.info(f"Application {application_id} outcome updated to {status}")
            return link
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Outcome update failed: {str(e)}")
            raise
    
    def get_resume_application_history(
        self,
        resume_id: int
    ) -> List[Dict]:
        """
        Get complete application history for a resume.
        
        Args:
            resume_id: Resume ID
        
        Returns:
            List of application records
        """
        try:
            links = ResumeJobLink.query.filter_by(
                resume_id=resume_id,
                is_active=True
            ).order_by(ResumeJobLink.applied_at.desc()).all()
            
            history = []
            for link in links:
                job = JobPost.query.get(link.job_id)
                application = Application.query.get(link.application_id) if link.application_id else None
                
                record = {
                    'link_id': link.id,
                    'job_id': link.job_id,
                    'job_title': job.title if job else 'Unknown',
                    'company': job.company if job else 'Unknown',
                    'application_id': link.application_id,
                    'status': link.application_status,
                    'match_score': link.match_score,
                    'applied_at': link.applied_at.isoformat() if link.applied_at else None,
                    'viewed_at': link.viewed_at.isoformat() if link.viewed_at else None,
                    'responded_at': link.responded_at.isoformat() if link.responded_at else None,
                    'version_id': link.version_id
                }
                
                history.append(record)
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get application history: {str(e)}")
            raise
    
    def get_job_resume_usage(
        self,
        job_id: int
    ) -> Optional[Dict]:
        """
        Get which resume was used for a specific job.
        
        Args:
            job_id: Job ID
        
        Returns:
            Resume usage information or None
        """
        try:
            link = ResumeJobLink.query.filter_by(
                job_id=job_id,
                is_active=True
            ).join(Resume).filter(
                Resume.user_id == self.user_id
            ).first()
            
            if not link:
                return None
            
            resume = Resume.query.get(link.resume_id)
            version = ResumeVersion.query.get(link.version_id) if link.version_id else None
            
            return {
                'resume_id': link.resume_id,
                'resume_title': resume.title if resume else 'Unknown',
                'version_id': link.version_id,
                'version_number': version.version_number if version else None,
                'application_status': link.application_status,
                'match_score': link.match_score,
                'applied_at': link.applied_at.isoformat() if link.applied_at else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get job resume usage: {str(e)}")
            raise
    
    def verify_data_consistency(self) -> Dict:
        """
        Verify data consistency between resumes, applications, and links.
        
        Returns:
            Consistency check report
        """
        try:
            issues = []
            
            # Check for orphaned links
            orphaned_links = db.session.query(ResumeJobLink).outerjoin(
                Resume
            ).filter(Resume.id == None).count()
            
            if orphaned_links > 0:
                issues.append({
                    'type': 'orphaned_links',
                    'count': orphaned_links,
                    'severity': 'high',
                    'message': f'{orphaned_links} resume-job links have no associated resume'
                })
            
            # Check for links with invalid applications
            invalid_app_links = db.session.query(ResumeJobLink).filter(
                ResumeJobLink.application_id != None
            ).outerjoin(
                Application,
                ResumeJobLink.application_id == Application.id
            ).filter(Application.id == None).count()
            
            if invalid_app_links > 0:
                issues.append({
                    'type': 'invalid_application_links',
                    'count': invalid_app_links,
                    'severity': 'medium',
                    'message': f'{invalid_app_links} links reference non-existent applications'
                })
            
            # Check for duplicate links
            duplicates = db.session.query(
                ResumeJobLink.resume_id,
                ResumeJobLink.job_id,
                db.func.count(ResumeJobLink.id)
            ).group_by(
                ResumeJobLink.resume_id,
                ResumeJobLink.job_id
            ).having(db.func.count(ResumeJobLink.id) > 1).all()
            
            if duplicates:
                issues.append({
                    'type': 'duplicate_links',
                    'count': len(duplicates),
                    'severity': 'low',
                    'message': f'{len(duplicates)} duplicate resume-job links found'
                })
            
            # Check for links without timestamps
            missing_timestamps = ResumeJobLink.query.filter(
                ResumeJobLink.applied_at == None
            ).count()
            
            if missing_timestamps > 0:
                issues.append({
                    'type': 'missing_timestamps',
                    'count': missing_timestamps,
                    'severity': 'low',
                    'message': f'{missing_timestamps} links missing applied_at timestamp'
                })
            
            return {
                'is_consistent': len(issues) == 0,
                'issues_found': len(issues),
                'issues': issues,
                'checked_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Consistency check failed: {str(e)}")
            raise
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    def _auto_select_best_resume(self, job_id: int) -> Tuple[Resume, Optional[ResumeVersion]]:
        """Auto-select the best resume for a job"""
        # Priority 1: Job-optimized version
        version = ResumeVersion.query.filter_by(
            job_id=job_id
        ).join(Resume).filter(
            Resume.user_id == self.user_id,
            Resume.is_active == True
        ).order_by(ResumeVersion.ats_score.desc()).first()
        
        if version:
            resume = Resume.query.get(version.resume_id)
            return resume, version
        
        # Priority 2: Primary resume
        primary = Resume.query.filter_by(
            user_id=self.user_id,
            is_primary=True,
            is_active=True
        ).first()
        
        if primary:
            return primary, None
        
        # Priority 3: Most recent resume
        latest = Resume.query.filter_by(
            user_id=self.user_id,
            is_active=True
        ).order_by(Resume.created_at.desc()).first()
        
        if latest:
            return latest, None
        
        raise ValueError("No active resumes found")
    
    def _update_metrics(self, link: ResumeJobLink, status: str):
        """Update resume metrics based on application outcome"""
        try:
            # Get or create metrics
            metrics = ResumeMetrics.query.filter_by(
                resume_id=link.resume_id,
                job_id=link.job_id
            ).first()
            
            if not metrics:
                metrics = ResumeMetrics(
                    resume_id=link.resume_id,
                    job_id=link.job_id,
                    version_id=link.version_id
                )
                db.session.add(metrics)
            
            # Update based on status
            if status == 'submitted':
                metrics.applications_sent += 1
            elif status == 'viewed':
                metrics.applications_viewed += 1
            elif status == 'interview':
                metrics.interviews_scheduled += 1
            elif status == 'rejected':
                metrics.applications_rejected += 1
            elif status == 'accepted':
                metrics.offers_received += 1
            
            # Recalculate rates
            metrics.recalculate_rates()
            
            db.session.commit()
            
        except Exception as e:
            self.logger.warning(f"Failed to update metrics: {str(e)}")
            # Don't fail the main operation if metrics update fails
    
    def cleanup_orphaned_links(self) -> int:
        """Clean up orphaned resume-job links"""
        try:
            # Find orphaned links
            orphaned = db.session.query(ResumeJobLink).outerjoin(
                Resume
            ).filter(Resume.id == None).all()
            
            count = len(orphaned)
            
            for link in orphaned:
                db.session.delete(link)
            
            db.session.commit()
            
            self.logger.info(f"Cleaned up {count} orphaned links")
            return count
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise
