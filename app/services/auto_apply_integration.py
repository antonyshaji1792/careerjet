"""
Auto-Apply Pipeline Integration Hooks
Integrates Resume Builder with Auto-Apply system
"""

from typing import Dict, Optional
import logging

from app.services.resume_job_link_service import ResumeJobLinkService
from app.services.ats_scoring_service import ATSScoringService
from app.models.resume import Resume
from app.models.application import Application
from app.extensions import db

logger = logging.getLogger(__name__)


class AutoApplyResumeIntegration:
    """
    Integration hooks for Resume Builder in Auto-Apply pipeline.
    Handles resume selection, optimization, and tracking.
    """
    
    @staticmethod
    def before_application(
        user_id: int,
        job_id: int,
        job_description: str,
        resume_id: Optional[int] = None
    ) -> Dict:
        """
        Hook called before submitting an application.
        Selects and prepares the best resume.
        
        Args:
            user_id: User ID
            job_id: Job ID
            job_description: Job description text
            resume_id: Optional specific resume to use
        
        Returns:
            Dict with resume_id, version_id, and resume_data
        """
        try:
            link_service = ResumeJobLinkService(user_id)
            
            # Select best resume
            resume, version = link_service.select_resume_for_job(
                job_id=job_id,
                resume_id=resume_id,
                auto_select=True
            )
            
            # Get resume content
            if version:
                resume_data = version.content_json
                resume_id_to_use = resume.id
                version_id = version.id
            else:
                resume_data = resume.content_json
                resume_id_to_use = resume.id
                version_id = None
            
            # Calculate ATS score
            ats_service = ATSScoringService()
            ats_report = ats_service.calculate_ats_score(
                resume_data=resume_data,
                job_description=job_description
            )
            
            logger.info(f"Resume {resume_id_to_use} selected for job {job_id} (ATS: {ats_report['overall_score']})")
            
            return {
                'resume_id': resume_id_to_use,
                'version_id': version_id,
                'resume_data': resume_data,
                'ats_score': ats_report['overall_score'],
                'match_score': ats_report.get('keyword_analysis', {}).get('match_percentage', 0)
            }
            
        except Exception as e:
            logger.error(f"Before application hook failed: {str(e)}")
            raise
    
    @staticmethod
    def after_application_submitted(
        user_id: int,
        application_id: int,
        job_id: int,
        resume_id: int,
        version_id: Optional[int] = None,
        match_score: Optional[float] = None
    ) -> Dict:
        """
        Hook called after application is submitted.
        Links resume to application and locks version.
        
        Args:
            user_id: User ID
            application_id: Created application ID
            job_id: Job ID
            resume_id: Resume ID used
            version_id: Optional version ID
            match_score: Optional match score
        
        Returns:
            Dict with link_id and locked status
        """
        try:
            link_service = ResumeJobLinkService(user_id)
            
            # Link resume to application
            link = link_service.link_resume_to_application(
                application_id=application_id,
                resume_id=resume_id,
                job_id=job_id,
                version_id=version_id,
                match_score=match_score
            )
            
            # Lock version
            locked_version = link_service.lock_resume_version(
                resume_id=resume_id,
                job_id=job_id,
                application_id=application_id
            )
            
            logger.info(f"Application {application_id} linked to resume {resume_id}")
            
            return {
                'link_id': link.id,
                'locked_version_id': locked_version.id,
                'locked': True
            }
            
        except Exception as e:
            logger.error(f"After application hook failed: {str(e)}")
            raise
    
    @staticmethod
    def on_application_status_change(
        user_id: int,
        application_id: int,
        new_status: str,
        details: Optional[Dict] = None
    ) -> Dict:
        """
        Hook called when application status changes.
        Updates outcome tracking and metrics.
        
        Args:
            user_id: User ID
            application_id: Application ID
            new_status: New status
            details: Optional additional details
        
        Returns:
            Dict with updated status
        """
        try:
            link_service = ResumeJobLinkService(user_id)
            
            # Update outcome
            link = link_service.update_application_outcome(
                application_id=application_id,
                status=new_status,
                outcome_details=details
            )
            
            logger.info(f"Application {application_id} status updated to {new_status}")
            
            return {
                'link_id': link.id,
                'status': new_status,
                'updated': True
            }
            
        except Exception as e:
            logger.error(f"Status change hook failed: {str(e)}")
            raise
    
    @staticmethod
    def get_application_resume_info(
        user_id: int,
        application_id: int
    ) -> Optional[Dict]:
        """
        Get resume information for an application.
        
        Args:
            user_id: User ID
            application_id: Application ID
        
        Returns:
            Resume info or None
        """
        try:
            from app.models.resume_links import ResumeJobLink
            
            link = ResumeJobLink.query.filter_by(
                application_id=application_id
            ).first()
            
            if not link:
                return None
            
            resume = Resume.query.get(link.resume_id)
            
            if not resume or resume.user_id != user_id:
                return None
            
            return {
                'resume_id': link.resume_id,
                'resume_title': resume.title,
                'version_id': link.version_id,
                'match_score': link.match_score,
                'ats_score': resume.ats_score
            }
            
        except Exception as e:
            logger.error(f"Failed to get application resume info: {str(e)}")
            return None
    
    @staticmethod
    def validate_resume_for_application(
        user_id: int,
        resume_id: int,
        job_description: str
    ) -> Dict:
        """
        Validate if a resume is suitable for a job.
        
        Args:
            user_id: User ID
            resume_id: Resume ID
            job_description: Job description
        
        Returns:
            Validation result
        """
        try:
            resume = Resume.query.filter_by(
                id=resume_id,
                user_id=user_id,
                is_active=True
            ).first()
            
            if not resume:
                return {
                    'valid': False,
                    'reason': 'Resume not found or not accessible'
                }
            
            # Check ATS score
            ats_service = ATSScoringService()
            ats_report = ats_service.calculate_ats_score(
                resume_data=resume.content_json,
                job_description=job_description
            )
            
            score = ats_report['overall_score']
            
            # Validation thresholds
            if score < 50:
                return {
                    'valid': False,
                    'reason': f'ATS score too low ({score}/100)',
                    'ats_score': score,
                    'recommendation': 'Optimize resume before applying'
                }
            elif score < 70:
                return {
                    'valid': True,
                    'warning': f'ATS score is moderate ({score}/100)',
                    'ats_score': score,
                    'recommendation': 'Consider optimizing resume'
                }
            else:
                return {
                    'valid': True,
                    'ats_score': score,
                    'message': 'Resume is well-optimized for this job'
                }
            
        except Exception as e:
            logger.error(f"Resume validation failed: {str(e)}")
            return {
                'valid': False,
                'reason': f'Validation error: {str(e)}'
            }


# Integration with existing Autopilot service
def integrate_with_autopilot():
    """
    Integrate Resume Builder hooks with Autopilot service.
    This function should be called during application initialization.
    """
    try:
        from app.services.autopilot import Autopilot
        
        # Store original methods
        original_apply = getattr(Autopilot, 'apply_to_job', None)
        original_update_status = getattr(Autopilot, 'update_application_status', None)
        
        if not original_apply:
            logger.warning("Autopilot.apply_to_job not found, skipping integration")
            return
        
        # Wrap apply_to_job method
        def wrapped_apply_to_job(self, job_id: int, **kwargs):
            """Wrapped apply_to_job with resume integration"""
            user_id = self.user_id
            
            # Get job details
            job = self.get_job_details(job_id)
            job_description = job.get('description', '')
            
            # Before application hook
            resume_info = AutoApplyResumeIntegration.before_application(
                user_id=user_id,
                job_id=job_id,
                job_description=job_description,
                resume_id=kwargs.get('resume_id')
            )
            
            # Add resume data to kwargs
            kwargs['resume_data'] = resume_info['resume_data']
            kwargs['resume_id'] = resume_info['resume_id']
            
            # Call original method
            result = original_apply(self, job_id, **kwargs)
            
            # After application hook
            if result.get('success') and result.get('application_id'):
                link_info = AutoApplyResumeIntegration.after_application_submitted(
                    user_id=user_id,
                    application_id=result['application_id'],
                    job_id=job_id,
                    resume_id=resume_info['resume_id'],
                    version_id=resume_info.get('version_id'),
                    match_score=resume_info.get('match_score')
                )
                
                result['resume_link_id'] = link_info['link_id']
                result['resume_locked'] = link_info['locked']
            
            return result
        
        # Wrap update_application_status method
        if original_update_status:
            def wrapped_update_status(self, application_id: int, new_status: str, **kwargs):
                """Wrapped update_application_status with resume integration"""
                user_id = self.user_id
                
                # Call original method
                result = original_update_status(self, application_id, new_status, **kwargs)
                
                # Status change hook
                try:
                    AutoApplyResumeIntegration.on_application_status_change(
                        user_id=user_id,
                        application_id=application_id,
                        new_status=new_status,
                        details=kwargs.get('details')
                    )
                except Exception as e:
                    logger.warning(f"Status change hook failed: {str(e)}")
                
                return result
            
            # Replace methods
            Autopilot.update_application_status = wrapped_update_status
        
        # Replace methods
        Autopilot.apply_to_job = wrapped_apply_to_job
        
        logger.info("Resume Builder successfully integrated with Autopilot")
        
    except ImportError:
        logger.warning("Autopilot service not found, skipping integration")
    except Exception as e:
        logger.error(f"Autopilot integration failed: {str(e)}")
