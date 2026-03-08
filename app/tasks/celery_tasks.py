from app.celery_app import celery
from app import create_app, db
from app.models import User, JobMatch, Schedule, Application
from app.services.ingestion import JobIngestionService
from app.services.matching import update_matches_for_user
from app.services.automation import AutoApplyService
from app.services.autopilot import Autopilot
from datetime import datetime
import asyncio
import random
import logging

# New imports for Selenium Engine
from app.services.naukri_apply_engine import SeleniumNaukriApplyEngine

logger = logging.getLogger(__name__)

@celery.task
def ingest_jobs_task(query='Python Developer'):
    app = create_app()
    with app.app_context():
        service = JobIngestionService()
        count = service.ingest_jobs(query)
        
        # After ingestion, update matches for all users
        users = User.query.all()
        for user in users:
            update_matches_for_user(user.id)
        
        return f"Ingested {count} jobs and updated matches."

@celery.task(bind=True, max_retries=3)
def auto_apply_task(self):
    """
    Refactored Auto-Apply Task using Selenium Engine.
    Runs strictly one at a time per worker to respect memory and detection limits.
    """
    app = create_app()
    with app.app_context():
        logger.info("Starting Auto-Apply Task Cycle...")
        
        # 1. Selection Strategy
        # Find users who have Auto-Apply enabled AND haven't reached their daily limit
        # This is a basic scheduling logic. In production, we might queue specific users.
        users = User.query.join(Schedule).filter(Schedule.is_auto_apply_enabled == True).all()
        
        active_users_count = 0
        
        for user in users:
            schedule = user.schedule
            
            # Basic Limit Check
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
            applied_today = Application.query.filter(
                Application.user_id == user.id,
                Application.applied_at >= today_start
            ).count()
            
            if applied_today >= (schedule.daily_limit or 5):
                logger.info(f"User {user.email} reached daily limit ({applied_today}). Skipping.")
                continue

            # 2. Execute Selenium Engine
            # We instantiate the engine specifically for this user
            engine = None
            try:
                logger.info(f"Launching Naukri Engine for User {user.email}")
                engine = SeleniumNaukriApplyEngine(user.id)
                engine.start_driver()
                
                # Perform Login
                if not engine.login():
                    logger.error(f"Failed to login for User {user.email}. Check credentials.")
                    continue
                
                # Perform Apply
                # Note: 'keywords' and 'location' should ideally come from user preferences. 
                # We default to 'Python' if not set, or fetch from their profile/schedule.
                keywords = "Software Engineer" # Placeholder: Connect this to User.preferences later
                location = "Remote"
                
                logger.info(f"Applying for jobs: {keywords} in {location}")
                engine.apply_easy_apply_jobs(limit=1) # Apply to 1 job per cycle per user to distribute load
                
                active_users_count += 1
                
            except Exception as e:
                logger.error(f"Error in auto-apply flow for user {user.id}: {e}")
                # We don't raise immediately to allow other users to be processed
                # But we might retry this specific user via a separate mechanism
            finally:
                if engine:
                    engine.stop_driver()
        
        return f"Auto-apply cycle completed. Processed {active_users_count} users."

@celery.task
def apply_to_linkedin_job_task(user_id, job_id, application_id):
    """
    Background task to process a single LinkedIn Easy Apply application
    """
    app = create_app()
    with app.app_context():
        from app.services.linkedin_easy_apply import apply_to_linkedin_job
        import asyncio
        
        try:
            # We use a new event loop for each task to avoid issues with closed loops
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(apply_to_linkedin_job(user_id, job_id, application_id))
            loop.close()
            return result
        except Exception as e:
            from app.models import Application
            application = Application.query.get(application_id)
            if application:
                application.status = 'Failed'
                application.error_message = f"Celery Task Error: {str(e)}"
                db.session.commit()
            return {'success': False, 'message': str(e)}

@celery.task
def run_all_autopilots_task():
    """
    Background task to run autopilot for all users who have it enabled.
    This respects daily search and application limits.
    """
    app = create_app()
    with app.app_context():
        # Find users with autopilot enabled
        users_with_autopilot = User.query.join(Schedule).filter(Schedule.is_autopilot_enabled == True).all()
        
        now = datetime.utcnow()
        day_name = now.strftime('%A')
        current_time_str = now.strftime('%H:%M')
        
        processed_users_count = 0
        
        for user in users_with_autopilot:
            schedule = user.schedule
            if not schedule: 
                continue
            
            # 1. Check if today is a preferred day
            if schedule.preferred_days and day_name not in schedule.preferred_days:
                continue
                
            # 2. Check if current time is within preferred window (e.g., "09:00-17:00")
            if schedule.preferred_time and '-' in schedule.preferred_time:
                try:
                    start_str, end_str = schedule.preferred_time.split('-')
                    # Simple string comparison works for HH:MM format
                    if not (start_str <= current_time_str <= end_str):
                        continue
                except Exception as e:
                    logger.error(f"Error parsing time window for user {user.id}: {e}")
                    continue # Skip this user if time parsing fails
            
            print(f"Starting Autopilot for user: {user.email}")
            
            # Initialize Autopilot
            autopilot = Autopilot(user.id)
            
            # Run Autopilot cycle
            try:
                # Update last run timestamp
                schedule.last_run_at = datetime.utcnow()
                db.session.commit()
                
                # run() now handles all enabled platforms (LinkedIn, Naukri, Indeed, etc.)
                asyncio.run(autopilot.run(limit_per_alert=schedule.daily_search_limit))
                processed_users_count += 1
            except Exception as e:
                logger.error(f"Background autopilot failed for user {user.id}: {str(e)}")
            
        return f"Processed autopilot for {processed_users_count} users."

@celery.task
def optimize_resume_task(user_id, resume_id, job_description, job_id=None):
    """
    Background task to optimize a resume for a specific job.
    Useful for bulk processing or long job descriptions.
    """
    app = create_app()
    with app.app_context():
        from app.services.resume_builder import ResumeBuilder
        from app.models import Resume, ResumeOptimization, db
        import asyncio
        import json
        
        try:
            service = ResumeBuilder(user_id)
            # Run async service in sync celery worker
            optimization_result = asyncio.run(service.optimize_for_job(resume_id, job_description))
            
            opt = ResumeOptimization(
                resume_id=resume_id,
                job_id=job_id,
                optimized_content=json.dumps(optimization_result.get('tailored_summary', '')),
                ats_score=optimization_result.get('ats_score', 0),
                missing_keywords=",".join(optimization_result.get('missing_keywords', [])),
                suggestions=",".join(optimization_result.get('suggestions', []))
            )
            db.session.add(opt)
            db.session.commit()
            return {'success': True, 'optimization_id': opt.id}
        except Exception as e:
            return {'success': False, 'error': str(e)}
