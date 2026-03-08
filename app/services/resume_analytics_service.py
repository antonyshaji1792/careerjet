"""
Resume Analytics Service
Provides comprehensive analytics for resume performance tracking
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc, case
from collections import defaultdict
import logging

from app.extensions import db
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.models.resume_links import ResumeJobLink, ATSScore
from app.models.resume_metrics import ResumeMetrics
from app.models.jobs import JobPost

logger = logging.getLogger(__name__)


class ResumeAnalyticsService:
    """
    Service for generating resume performance analytics.
    Provides insights on ATS scores, keyword coverage, conversions, and success rates.
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.logger = logger
    
    def get_dashboard_metrics(
        self,
        days: int = 30,
        resume_id: Optional[int] = None
    ) -> Dict:
        """
        Get comprehensive dashboard metrics.
        
        Args:
            days: Number of days to analyze
            resume_id: Optional specific resume ID
        
        Returns:
            Complete dashboard metrics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all metrics
            ats_trends = self.get_ats_score_trends(days, resume_id)
            keyword_trends = self.get_keyword_coverage_trends(days, resume_id)
            conversion_rates = self.get_interview_conversion_rates(resume_id)
            top_skills = self.get_best_performing_skills(days)
            success_rates = self.get_resume_job_success_rates(resume_id)
            
            # Summary stats
            summary = self._calculate_summary_stats(
                start_date,
                resume_id
            )
            
            return {
                'summary': summary,
                'ats_score_trends': ats_trends,
                'keyword_coverage_trends': keyword_trends,
                'interview_conversion_rates': conversion_rates,
                'best_performing_skills': top_skills,
                'resume_job_success_rates': success_rates,
                'period': {
                    'days': days,
                    'start_date': start_date.isoformat(),
                    'end_date': datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Dashboard metrics failed: {str(e)}")
            raise
    
    def get_ats_score_trends(
        self,
        days: int = 30,
        resume_id: Optional[int] = None
    ) -> Dict:
        """
        Get ATS score trends over time.
        
        Args:
            days: Number of days to analyze
            resume_id: Optional specific resume ID
        
        Returns:
            ATS score trend data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Build query
            query = db.session.query(
                func.date(ATSScore.created_at).label('date'),
                func.avg(ATSScore.overall_score).label('avg_score'),
                func.max(ATSScore.overall_score).label('max_score'),
                func.min(ATSScore.overall_score).label('min_score'),
                func.count(ATSScore.id).label('count')
            ).join(
                Resume,
                ATSScore.resume_id == Resume.id
            ).filter(
                Resume.user_id == self.user_id,
                ATSScore.created_at >= start_date
            )
            
            if resume_id:
                query = query.filter(ATSScore.resume_id == resume_id)
            
            results = query.group_by(
                func.date(ATSScore.created_at)
            ).order_by(
                func.date(ATSScore.created_at)
            ).all()
            
            # Format data
            trend_data = []
            for row in results:
                trend_data.append({
                    'date': row.date.isoformat(),
                    'avg_score': round(float(row.avg_score), 1),
                    'max_score': round(float(row.max_score), 1),
                    'min_score': round(float(row.min_score), 1),
                    'count': row.count
                })
            
            # Calculate overall trend
            if len(trend_data) >= 2:
                first_avg = trend_data[0]['avg_score']
                last_avg = trend_data[-1]['avg_score']
                trend_direction = 'up' if last_avg > first_avg else 'down' if last_avg < first_avg else 'stable'
                trend_change = round(last_avg - first_avg, 1)
            else:
                trend_direction = 'stable'
                trend_change = 0
            
            return {
                'data': trend_data,
                'trend': {
                    'direction': trend_direction,
                    'change': trend_change
                },
                'current_avg': trend_data[-1]['avg_score'] if trend_data else 0
            }
            
        except Exception as e:
            self.logger.error(f"ATS trends failed: {str(e)}")
            raise
    
    def get_keyword_coverage_trends(
        self,
        days: int = 30,
        resume_id: Optional[int] = None
    ) -> Dict:
        """
        Get keyword coverage trends over time.
        
        Args:
            days: Number of days to analyze
            resume_id: Optional specific resume ID
        
        Returns:
            Keyword coverage trend data
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Query keyword match percentages
            query = db.session.query(
                func.date(ATSScore.created_at).label('date'),
                func.avg(ATSScore.keyword_match_percentage).label('avg_coverage'),
                func.count(ATSScore.id).label('count')
            ).join(
                Resume,
                ATSScore.resume_id == Resume.id
            ).filter(
                Resume.user_id == self.user_id,
                ATSScore.created_at >= start_date,
                ATSScore.keyword_match_percentage.isnot(None)
            )
            
            if resume_id:
                query = query.filter(ATSScore.resume_id == resume_id)
            
            results = query.group_by(
                func.date(ATSScore.created_at)
            ).order_by(
                func.date(ATSScore.created_at)
            ).all()
            
            # Format data
            trend_data = []
            for row in results:
                trend_data.append({
                    'date': row.date.isoformat(),
                    'avg_coverage': round(float(row.avg_coverage), 1),
                    'count': row.count
                })
            
            return {
                'data': trend_data,
                'current_avg': trend_data[-1]['avg_coverage'] if trend_data else 0
            }
            
        except Exception as e:
            self.logger.error(f"Keyword trends failed: {str(e)}")
            raise
    
    def get_interview_conversion_rates(
        self,
        resume_id: Optional[int] = None
    ) -> Dict:
        """
        Get interview conversion rates per resume.
        
        Args:
            resume_id: Optional specific resume ID
        
        Returns:
            Conversion rate data
        """
        try:
            # Query applications and interviews per resume
            query = db.session.query(
                Resume.id.label('resume_id'),
                Resume.title.label('resume_title'),
                func.count(ResumeJobLink.id).label('total_applications'),
                func.sum(
                    case(
                        (ResumeJobLink.application_status == 'interview', 1),
                        else_=0
                    )
                ).label('interviews'),
                func.sum(
                    case(
                        (ResumeJobLink.application_status == 'accepted', 1),
                        else_=0
                    )
                ).label('offers')
            ).join(
                ResumeJobLink,
                Resume.id == ResumeJobLink.resume_id
            ).filter(
                Resume.user_id == self.user_id,
                ResumeJobLink.is_active == True
            )
            
            if resume_id:
                query = query.filter(Resume.id == resume_id)
            
            results = query.group_by(
                Resume.id,
                Resume.title
            ).all()
            
            # Calculate rates
            conversion_data = []
            for row in results:
                total = row.total_applications
                interviews = row.interviews or 0
                offers = row.offers or 0
                
                interview_rate = (interviews / total * 100) if total > 0 else 0
                offer_rate = (offers / total * 100) if total > 0 else 0
                
                conversion_data.append({
                    'resume_id': row.resume_id,
                    'resume_title': row.resume_title,
                    'total_applications': total,
                    'interviews': interviews,
                    'offers': offers,
                    'interview_rate': round(interview_rate, 1),
                    'offer_rate': round(offer_rate, 1)
                })
            
            # Sort by interview rate
            conversion_data.sort(key=lambda x: x['interview_rate'], reverse=True)
            
            return {
                'by_resume': conversion_data,
                'overall': self._calculate_overall_conversion(conversion_data)
            }
            
        except Exception as e:
            self.logger.error(f"Conversion rates failed: {str(e)}")
            raise
    
    def get_best_performing_skills(
        self,
        days: int = 30,
        limit: int = 10
    ) -> Dict:
        """
        Get best-performing skills based on interview conversion.
        
        Args:
            days: Number of days to analyze
            limit: Number of top skills to return
        
        Returns:
            Top performing skills
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get all applications with resumes
            links = db.session.query(
                ResumeJobLink,
                Resume
            ).join(
                Resume,
                ResumeJobLink.resume_id == Resume.id
            ).filter(
                Resume.user_id == self.user_id,
                ResumeJobLink.applied_at >= start_date,
                ResumeJobLink.is_active == True
            ).all()
            
            # Aggregate by skill
            skill_stats = defaultdict(lambda: {
                'applications': 0,
                'interviews': 0,
                'offers': 0
            })
            
            for link, resume in links:
                # Extract skills from resume
                skills = resume.content_json.get('skills', [])
                
                for skill in skills:
                    skill_lower = skill.lower()
                    skill_stats[skill_lower]['applications'] += 1
                    
                    if link.application_status == 'interview':
                        skill_stats[skill_lower]['interviews'] += 1
                    elif link.application_status == 'accepted':
                        skill_stats[skill_lower]['offers'] += 1
            
            # Calculate rates
            skill_performance = []
            for skill, stats in skill_stats.items():
                total = stats['applications']
                if total >= 3:  # Minimum 3 applications
                    interview_rate = (stats['interviews'] / total * 100)
                    offer_rate = (stats['offers'] / total * 100)
                    
                    skill_performance.append({
                        'skill': skill.title(),
                        'applications': total,
                        'interviews': stats['interviews'],
                        'offers': stats['offers'],
                        'interview_rate': round(interview_rate, 1),
                        'offer_rate': round(offer_rate, 1),
                        'score': round(interview_rate * 0.7 + offer_rate * 0.3, 1)
                    })
            
            # Sort by score
            skill_performance.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'top_skills': skill_performance[:limit],
                'total_skills_analyzed': len(skill_stats)
            }
            
        except Exception as e:
            self.logger.error(f"Skill performance failed: {str(e)}")
            raise
    
    def get_resume_job_success_rates(
        self,
        resume_id: Optional[int] = None
    ) -> Dict:
        """
        Get success rates for resume-job combinations.
        
        Args:
            resume_id: Optional specific resume ID
        
        Returns:
            Success rate data
        """
        try:
            # Query success metrics
            query = db.session.query(
                Resume.id.label('resume_id'),
                Resume.title.label('resume_title'),
                JobPost.title.label('job_title'),
                JobPost.company.label('company'),
                ResumeJobLink.match_score,
                ResumeJobLink.application_status,
                func.count(ResumeJobLink.id).label('count')
            ).join(
                ResumeJobLink,
                Resume.id == ResumeJobLink.resume_id
            ).join(
                JobPost,
                ResumeJobLink.job_id == JobPost.id
            ).filter(
                Resume.user_id == self.user_id,
                ResumeJobLink.is_active == True
            )
            
            if resume_id:
                query = query.filter(Resume.id == resume_id)
            
            results = query.group_by(
                Resume.id,
                Resume.title,
                JobPost.title,
                JobPost.company,
                ResumeJobLink.match_score,
                ResumeJobLink.application_status
            ).all()
            
            # Aggregate by resume-job type
            job_type_stats = defaultdict(lambda: {
                'applications': 0,
                'interviews': 0,
                'offers': 0,
                'avg_match_score': []
            })
            
            for row in results:
                # Extract job type (simplified)
                job_type = self._extract_job_type(row.job_title)
                
                job_type_stats[job_type]['applications'] += row.count
                
                if row.application_status == 'interview':
                    job_type_stats[job_type]['interviews'] += row.count
                elif row.application_status == 'accepted':
                    job_type_stats[job_type]['offers'] += row.count
                
                if row.match_score:
                    job_type_stats[job_type]['avg_match_score'].append(float(row.match_score))
            
            # Calculate rates
            success_data = []
            for job_type, stats in job_type_stats.items():
                total = stats['applications']
                if total > 0:
                    avg_match = sum(stats['avg_match_score']) / len(stats['avg_match_score']) if stats['avg_match_score'] else 0
                    
                    success_data.append({
                        'job_type': job_type,
                        'applications': total,
                        'interviews': stats['interviews'],
                        'offers': stats['offers'],
                        'success_rate': round((stats['interviews'] + stats['offers']) / total * 100, 1),
                        'avg_match_score': round(avg_match, 1)
                    })
            
            # Sort by success rate
            success_data.sort(key=lambda x: x['success_rate'], reverse=True)
            
            return {
                'by_job_type': success_data,
                'total_job_types': len(success_data)
            }
            
        except Exception as e:
            self.logger.error(f"Success rates failed: {str(e)}")
            raise
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _calculate_summary_stats(
        self,
        start_date: datetime,
        resume_id: Optional[int]
    ) -> Dict:
        """Calculate summary statistics"""
        try:
            # Total applications
            app_query = db.session.query(
                func.count(ResumeJobLink.id)
            ).join(
                Resume,
                ResumeJobLink.resume_id == Resume.id
            ).filter(
                Resume.user_id == self.user_id,
                ResumeJobLink.applied_at >= start_date
            )
            
            if resume_id:
                app_query = app_query.filter(Resume.id == resume_id)
            
            total_applications = app_query.scalar() or 0
            
            # Interview count
            interview_query = db.session.query(
                func.count(ResumeJobLink.id)
            ).join(
                Resume,
                ResumeJobLink.resume_id == Resume.id
            ).filter(
                Resume.user_id == self.user_id,
                ResumeJobLink.applied_at >= start_date,
                ResumeJobLink.application_status == 'interview'
            )
            
            if resume_id:
                interview_query = interview_query.filter(Resume.id == resume_id)
            
            total_interviews = interview_query.scalar() or 0
            
            # Average ATS score
            ats_query = db.session.query(
                func.avg(ATSScore.overall_score)
            ).join(
                Resume,
                ATSScore.resume_id == Resume.id
            ).filter(
                Resume.user_id == self.user_id,
                ATSScore.created_at >= start_date
            )
            
            if resume_id:
                ats_query = ats_query.filter(Resume.id == resume_id)
            
            avg_ats = ats_query.scalar() or 0
            
            # Active resumes
            active_resumes = Resume.query.filter_by(
                user_id=self.user_id,
                is_active=True
            ).count()
            
            return {
                'total_applications': total_applications,
                'total_interviews': total_interviews,
                'interview_rate': round((total_interviews / total_applications * 100) if total_applications > 0 else 0, 1),
                'avg_ats_score': round(float(avg_ats), 1),
                'active_resumes': active_resumes
            }
            
        except Exception as e:
            self.logger.error(f"Summary stats failed: {str(e)}")
            return {
                'total_applications': 0,
                'total_interviews': 0,
                'interview_rate': 0,
                'avg_ats_score': 0,
                'active_resumes': 0
            }
    
    def _calculate_overall_conversion(self, conversion_data: List[Dict]) -> Dict:
        """Calculate overall conversion rates"""
        if not conversion_data:
            return {
                'total_applications': 0,
                'total_interviews': 0,
                'total_offers': 0,
                'interview_rate': 0,
                'offer_rate': 0
            }
        
        total_apps = sum(r['total_applications'] for r in conversion_data)
        total_interviews = sum(r['interviews'] for r in conversion_data)
        total_offers = sum(r['offers'] for r in conversion_data)
        
        return {
            'total_applications': total_apps,
            'total_interviews': total_interviews,
            'total_offers': total_offers,
            'interview_rate': round((total_interviews / total_apps * 100) if total_apps > 0 else 0, 1),
            'offer_rate': round((total_offers / total_apps * 100) if total_apps > 0 else 0, 1)
        }
    
    def _extract_job_type(self, job_title: str) -> str:
        """Extract job type from title"""
        title_lower = job_title.lower()
        
        if 'senior' in title_lower or 'lead' in title_lower or 'principal' in title_lower:
            return 'Senior'
        elif 'junior' in title_lower or 'entry' in title_lower:
            return 'Junior'
        elif 'engineer' in title_lower:
            return 'Engineer'
        elif 'developer' in title_lower:
            return 'Developer'
        elif 'data' in title_lower:
            return 'Data'
        elif 'manager' in title_lower:
            return 'Manager'
        else:
            return 'Other'
