"""
Job Alerts Service

This module handles job alert notifications via email.
Users can set up custom alerts based on keywords, location, and other criteria.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os
import logging
from app.models import JobPost, UserProfile
from app import db

logger = logging.getLogger(__name__)


class JobAlertsService:
    """Manage job alerts and notifications"""
    
    def __init__(self):
        from app.models import SystemConfig
        self.smtp_server = SystemConfig.get_config_value('SMTP_SERVER', os.getenv('SMTP_SERVER', 'smtp.gmail.com'))
        self.smtp_port = int(SystemConfig.get_config_value('SMTP_PORT', os.getenv('SMTP_PORT', '587')))
        self.smtp_username = SystemConfig.get_config_value('SMTP_USER', os.getenv('SMTP_USERNAME', ''))
        self.smtp_password = SystemConfig.get_config_value('SMTP_PASSWORD', os.getenv('SMTP_PASSWORD', ''))
        self.from_email = SystemConfig.get_config_value('SMTP_FROM_EMAIL', os.getenv('FROM_EMAIL', 'noreply@careerjet.com'))
        self.use_tls = SystemConfig.get_config_value('SMTP_USE_TLS', 'true') == 'true'
    
    def send_email(self, to_email, subject, html_content):
        """
        Send an email notification
        
        Args:
            to_email (str): Recipient email
            subject (str): Email subject
            html_content (str): HTML email body
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                    
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False
    
    def check_for_new_jobs(self, alert_config):
        """
        Check for new jobs matching alert criteria
        
        Args:
            alert_config (dict): Alert configuration
                - keywords (str): Job keywords
                - location (str): Location filter
                - platforms (list): List of platforms to check
                - last_checked (datetime): Last check time
                
        Returns:
            list: List of matching jobs
        """
        try:
            # Build query
            query = JobPost.query
            
            # Filter by time (only new jobs since last check)
            last_checked = alert_config.get('last_checked', datetime.utcnow() - timedelta(days=1))
            query = query.filter(JobPost.ingested_at > last_checked)
            
            # Filter by keywords
            keywords = alert_config.get('keywords', '')
            if keywords:
                keyword_list = [k.strip() for k in keywords.split(',')]
                keyword_filters = []
                for keyword in keyword_list:
                    keyword_filters.append(JobPost.title.ilike(f'%{keyword}%'))
                    keyword_filters.append(JobPost.description.ilike(f'%{keyword}%'))
                
                # Combine with OR
                from sqlalchemy import or_
                query = query.filter(or_(*keyword_filters))
            
            # Filter by location
            location = alert_config.get('location', '')
            if location:
                query = query.filter(JobPost.location.ilike(f'%{location}%'))
            
            # Filter by platforms
            platforms = alert_config.get('platforms', [])
            if platforms:
                query = query.filter(JobPost.platform.in_(platforms))
            
            # Get results
            jobs = query.order_by(JobPost.ingested_at.desc()).limit(50).all()
            
            logger.info(f"Found {len(jobs)} new jobs matching alert criteria")
            return jobs
            
        except Exception as e:
            logger.error(f"Error checking for new jobs: {str(e)}")
            return []
    
    def send_job_alert(self, user_email, user_name, jobs, alert_name):
        """
        Send job alert email with matching jobs
        
        Args:
            user_email (str): User's email
            user_name (str): User's name
            jobs (list): List of JobPost objects
            alert_name (str): Name of the alert
            
        Returns:
            bool: True if sent successfully
        """
        if not jobs:
            logger.info(f"No jobs to send for alert: {alert_name}")
            return False
        
        # Build email content
        subject = f"🎯 {len(jobs)} New Job{'s' if len(jobs) > 1 else ''} Matching '{alert_name}'"
        
        html_content = self._build_alert_email_html(user_name, jobs, alert_name)
        
        return self.send_email(user_email, subject, html_content)
    
    def send_daily_digest(self, user_email, user_name, all_alerts_jobs):
        """
        Send daily digest with all matching jobs
        
        Args:
            user_email (str): User's email
            user_name (str): User's name
            all_alerts_jobs (dict): Dictionary of alert_name -> jobs list
            
        Returns:
            bool: True if sent successfully
        """
        total_jobs = sum(len(jobs) for jobs in all_alerts_jobs.values())
        
        if total_jobs == 0:
            logger.info(f"No jobs for daily digest to {user_email}")
            return False
        
        subject = f"📊 Daily Job Digest: {total_jobs} New Opportunities"
        
        html_content = self._build_digest_email_html(user_name, all_alerts_jobs)
        
        return self.send_email(user_email, subject, html_content)
    
    def _build_alert_email_html(self, user_name, jobs, alert_name):
        """Build HTML for job alert email"""
        
        jobs_html = ""
        for job in jobs[:10]:  # Limit to 10 jobs per email
            jobs_html += f"""
            <div style="background: #f9fafb; border-left: 4px solid #6366f1; padding: 1rem; margin-bottom: 1rem; border-radius: 4px;">
                <h3 style="margin: 0 0 0.5rem 0; color: #1f2937;">
                    <a href="{job.job_url}" style="color: #6366f1; text-decoration: none;">{job.title}</a>
                </h3>
                <p style="margin: 0 0 0.5rem 0; color: #6b7280;">
                    <strong>{job.company}</strong> • {job.location or 'Location not specified'} • {job.platform}
                </p>
                <p style="margin: 0; color: #4b5563; font-size: 0.875rem;">
                    {job.description[:200] if job.description else 'No description available'}...
                </p>
                <a href="{job.job_url}" style="display: inline-block; margin-top: 0.75rem; color: #6366f1; text-decoration: none; font-weight: 600;">
                    View Job →
                </a>
            </div>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 2rem; border-radius: 8px; margin-bottom: 2rem; text-align: center;">
                <h1 style="margin: 0; font-size: 1.75rem;">🎯 New Jobs Alert</h1>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.95;">Alert: {alert_name}</p>
            </div>
            
            <p style="margin-bottom: 1.5rem;">Hi {user_name},</p>
            
            <p style="margin-bottom: 1.5rem;">
                We found <strong>{len(jobs)} new job{'s' if len(jobs) > 1 else ''}</strong> matching your alert criteria!
            </p>
            
            {jobs_html}
            
            {f'<p style="color: #6b7280; font-size: 0.875rem; margin-top: 1.5rem;">Showing {min(10, len(jobs))} of {len(jobs)} jobs. <a href="http://localhost:3000/jobs" style="color: #6366f1;">View all →</a></p>' if len(jobs) > 10 else ''}
            
            <div style="margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e5e7eb; text-align: center; color: #6b7280; font-size: 0.875rem;">
                <p>You're receiving this because you set up a job alert on CareerJet.</p>
                <p><a href="http://localhost:3000/alerts" style="color: #6366f1; text-decoration: none;">Manage your alerts</a></p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _build_digest_email_html(self, user_name, all_alerts_jobs):
        """Build HTML for daily digest email"""
        
        alerts_html = ""
        total_jobs = 0
        
        for alert_name, jobs in all_alerts_jobs.items():
            if not jobs:
                continue
            
            total_jobs += len(jobs)
            
            jobs_list = ""
            for job in jobs[:5]:  # Limit to 5 jobs per alert in digest
                jobs_list += f"""
                <li style="margin-bottom: 0.75rem;">
                    <a href="{job.job_url}" style="color: #6366f1; text-decoration: none; font-weight: 600;">{job.title}</a>
                    <br>
                    <span style="color: #6b7280; font-size: 0.875rem;">{job.company} • {job.location or 'Remote'}</span>
                </li>
                """
            
            alerts_html += f"""
            <div style="background: #f9fafb; padding: 1.5rem; margin-bottom: 1.5rem; border-radius: 8px;">
                <h3 style="margin: 0 0 1rem 0; color: #1f2937;">📌 {alert_name}</h3>
                <p style="margin: 0 0 1rem 0; color: #6b7280;">{len(jobs)} new job{'s' if len(jobs) > 1 else ''}</p>
                <ul style="margin: 0; padding-left: 1.5rem;">
                    {jobs_list}
                </ul>
                {f'<p style="color: #6b7280; font-size: 0.875rem; margin-top: 0.75rem;">+ {len(jobs) - 5} more jobs</p>' if len(jobs) > 5 else ''}
            </div>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; color: #1f2937; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 2rem; border-radius: 8px; margin-bottom: 2rem; text-align: center;">
                <h1 style="margin: 0; font-size: 1.75rem;">📊 Daily Job Digest</h1>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.95;">{datetime.now().strftime('%B %d, %Y')}</p>
            </div>
            
            <p style="margin-bottom: 1.5rem;">Hi {user_name},</p>
            
            <p style="margin-bottom: 1.5rem;">
                Here's your daily summary: <strong>{total_jobs} new job opportunities</strong> across {len(all_alerts_jobs)} alert{'s' if len(all_alerts_jobs) > 1 else ''}.
            </p>
            
            {alerts_html}
            
            <div style="text-align: center; margin: 2rem 0;">
                <a href="http://localhost:3000/jobs" style="display: inline-block; background: #6366f1; color: white; padding: 0.875rem 2rem; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    View All Jobs
                </a>
            </div>
            
            <div style="margin-top: 2rem; padding-top: 2rem; border-top: 1px solid #e5e7eb; text-align: center; color: #6b7280; font-size: 0.875rem;">
                <p>You're receiving this daily digest from CareerJet.</p>
                <p><a href="http://localhost:3000/alerts" style="color: #6366f1; text-decoration: none;">Manage your alerts</a> | <a href="http://localhost:3000/alerts/unsubscribe" style="color: #6b7280; text-decoration: none;">Unsubscribe</a></p>
            </div>
        </body>
        </html>
        """
        
        return html


# Helper function
def send_job_alert_email(user_email, user_name, jobs, alert_name):
    """
    Quick function to send a job alert
    
    Args:
        user_email (str): User's email
        user_name (str): User's name
        jobs (list): List of jobs
        alert_name (str): Alert name
        
    Returns:
        bool: True if sent successfully
    """
    service = JobAlertsService()
    return service.send_job_alert(user_email, user_name, jobs, alert_name)
