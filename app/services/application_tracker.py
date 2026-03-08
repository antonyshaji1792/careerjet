"""
Application Tracking Service

Provides Kanban-style tracking for job applications with stages and analytics.
"""

from app.models import Application, JobPost
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)


class ApplicationTracker:
    """Track and analyze job applications"""
    
    # Application stages
    STAGES = {
        'wishlist': {'name': 'Wishlist', 'order': 0, 'color': '#6b7280'},
        'applied': {'name': 'Applied', 'order': 1, 'color': '#3b82f6'},
        'screening': {'name': 'Screening', 'order': 2, 'color': '#8b5cf6'},
        'interview': {'name': 'Interview', 'order': 3, 'color': '#f59e0b'},
        'offer': {'name': 'Offer', 'order': 4, 'color': '#10b981'},
        'rejected': {'name': 'Rejected', 'order': 5, 'color': '#dc2626'},
        'accepted': {'name': 'Accepted', 'order': 6, 'color': '#059669'}
    }
    
    def get_applications_by_stage(self, user_id):
        """
        Get applications organized by stage
        
        Args:
            user_id (int): User ID
            
        Returns:
            dict: Applications grouped by stage
        """
        try:
            applications = Application.query.filter_by(user_id=user_id).all()
            
            by_stage = {stage: [] for stage in self.STAGES.keys()}
            
            for app in applications:
                stage = app.status.lower() if app.status else 'applied'
                
                # Map status to stage
                if stage in by_stage:
                    by_stage[stage].append(app)
                else:
                    by_stage['applied'].append(app)
            
            return by_stage
            
        except Exception as e:
            logger.error(f"Error getting applications by stage: {str(e)}")
            return {stage: [] for stage in self.STAGES.keys()}
    
    def move_application(self, application_id, new_stage):
        """
        Move application to a new stage
        
        Args:
            application_id (int): Application ID
            new_stage (str): New stage name
            
        Returns:
            bool: Success status
        """
        try:
            app = Application.query.get(application_id)
            
            if not app:
                return False
            
            if new_stage not in self.STAGES:
                return False
            
            app.status = self.STAGES[new_stage]['name']
            db.session.commit()
            
            logger.info(f"Moved application {application_id} to {new_stage}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error moving application: {str(e)}")
            return False
    
    def get_analytics(self, user_id, days=30):
        """
        Get application analytics
        
        Args:
            user_id (int): User ID
            days (int): Number of days to analyze
            
        Returns:
            dict: Analytics data
        """
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Total applications
            total = Application.query.filter_by(user_id=user_id).count()
            
            # Recent applications
            recent = Application.query.filter(
                Application.user_id == user_id,
                Application.applied_at >= since_date
            ).count()
            
            # By status
            by_status = db.session.query(
                Application.status,
                func.count(Application.id)
            ).filter(
                Application.user_id == user_id
            ).group_by(Application.status).all()
            
            status_counts = {status: count for status, count in by_status}
            
            # Response rate
            total_applied = Application.query.filter_by(user_id=user_id).count()
            responses = Application.query.filter(
                Application.user_id == user_id,
                Application.status.in_(['Screening', 'Interview', 'Offer'])
            ).count()
            
            response_rate = (responses / total_applied * 100) if total_applied > 0 else 0
            
            # Interview rate
            interviews = Application.query.filter(
                Application.user_id == user_id,
                Application.status.in_(['Interview', 'Offer'])
            ).count()
            
            interview_rate = (interviews / total_applied * 100) if total_applied > 0 else 0
            
            # Offer rate
            offers = Application.query.filter(
                Application.user_id == user_id,
                Application.status == 'Offer'
            ).count()
            
            offer_rate = (offers / total_applied * 100) if total_applied > 0 else 0
            
            # Average time to response (mock data for now)
            avg_response_time = 7  # days
            
            analytics = {
                'total_applications': total,
                'recent_applications': recent,
                'status_counts': status_counts,
                'response_rate': round(response_rate, 1),
                'interview_rate': round(interview_rate, 1),
                'offer_rate': round(offer_rate, 1),
                'avg_response_time': avg_response_time,
                'days_analyzed': days
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting analytics: {str(e)}")
            return {
                'total_applications': 0,
                'recent_applications': 0,
                'status_counts': {},
                'response_rate': 0,
                'interview_rate': 0,
                'offer_rate': 0,
                'avg_response_time': 0,
                'days_analyzed': days
            }
    
    def get_timeline(self, user_id, limit=20):
        """
        Get application timeline
        
        Args:
            user_id (int): User ID
            limit (int): Number of events
            
        Returns:
            list: Timeline events
        """
        try:
            applications = Application.query.filter_by(
                user_id=user_id
            ).order_by(
                Application.applied_at.desc()
            ).limit(limit).all()
            
            timeline = []
            
            for app in applications:
                job = JobPost.query.get(app.job_id)
                
                event = {
                    'date': app.applied_at,
                    'title': f'Applied to {job.title if job else "Unknown"}',
                    'company': job.company if job else 'Unknown',
                    'status': app.status,
                    'type': 'application'
                }
                
                timeline.append(event)
            
            return timeline
            
        except Exception as e:
            logger.error(f"Error getting timeline: {str(e)}")
            return []
    
    def get_success_metrics(self, user_id):
        """
        Get success metrics and insights
        
        Args:
            user_id (int): User ID
            
        Returns:
            dict: Success metrics
        """
        try:
            analytics = self.get_analytics(user_id, days=90)
            
            # Calculate success score (0-100)
            success_score = 0
            
            # Response rate contributes 40%
            success_score += analytics['response_rate'] * 0.4
            
            # Interview rate contributes 35%
            success_score += analytics['interview_rate'] * 0.35
            
            # Offer rate contributes 25%
            success_score += analytics['offer_rate'] * 0.25
            
            # Determine performance level
            if success_score >= 80:
                performance = 'Excellent'
                message = 'You\'re doing great! Keep up the good work.'
            elif success_score >= 60:
                performance = 'Good'
                message = 'You\'re on the right track. Consider optimizing your resume.'
            elif success_score >= 40:
                performance = 'Average'
                message = 'Room for improvement. Focus on tailoring applications.'
            else:
                performance = 'Needs Improvement'
                message = 'Consider revising your approach. Use AI tools to optimize.'
            
            metrics = {
                'success_score': round(success_score, 1),
                'performance_level': performance,
                'message': message,
                'total_applications': analytics['total_applications'],
                'response_rate': analytics['response_rate'],
                'interview_rate': analytics['interview_rate'],
                'offer_rate': analytics['offer_rate']
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting success metrics: {str(e)}")
            return {
                'success_score': 0,
                'performance_level': 'Unknown',
                'message': 'Not enough data',
                'total_applications': 0,
                'response_rate': 0,
                'interview_rate': 0,
                'offer_rate': 0
            }


# Helper function
def get_application_board(user_id):
    """
    Get Kanban board data for user
    
    Args:
        user_id (int): User ID
        
    Returns:
        dict: Board data with stages and applications
    """
    tracker = ApplicationTracker()
    
    return {
        'stages': tracker.STAGES,
        'applications': tracker.get_applications_by_stage(user_id),
        'analytics': tracker.get_analytics(user_id)
    }
