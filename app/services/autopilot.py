
import asyncio
import logging
import random
from datetime import datetime, date
from app.models import User, LinkedInCredentials, NaukriCredentials, LinkedInJob, Application, JobAlert, JobPost, UserProfile, Resume, Schedule, WebsitePreference, PlatformCredential
from app import db
from app.services.linkedin_scraper import LinkedInScraper
from app.services.linkedin_easy_apply import apply_to_linkedin_job
from app.services.naukri_scraper import NaukriScraper
from app.services.naukri_bot import apply_to_naukri_job
from app.services.scrapers_hub import ScraperFactory
from app.services.matching import MatchingEngine
from app.services.resume_service import ResumeService
import json

logger = logging.getLogger(__name__)

class Autopilot:
    """Service to autonomously scrape and apply for jobs across all supported platforms"""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.user = db.session.get(User, user_id)
        
    async def run(self, limit_per_alert=10):
        """Run the autopilot process for all enabled platforms"""
        if not self.user:
            return {'success': False, 'message': 'User not found'}
            
        # Get user's enabled platforms
        prefs = WebsitePreference.query.filter_by(user_id=self.user_id, is_enabled=True).all()
        enabled_platforms = [p.platform_name.lower() for p in prefs]
        
        if not enabled_platforms:
            # Multi-hop fallback if no preferences set
            enabled_platforms = ['linkedin', 'naukri'] # Removed 'indeed' as it's not fully implemented yet
            
        results = {
            'platforms_processed': [],
            'jobs_scraped': 0,
            'applications_sent': 0,
            'details': []
        }
        
        for platform in enabled_platforms:
            try:
                platform_result = await self.run_platform(platform, limit_per_alert=limit_per_alert)
                results['platforms_processed'].append(platform)
                results['jobs_scraped'] += platform_result.get('jobs_scraped', 0)
                results['applications_sent'] += platform_result.get('applications_sent', 0)
                results['details'].extend(platform_result.get('details', []))
            except Exception as e:
                logger.error(f"Error running autopilot for {platform}: {str(e)}")
                results['details'].append({'status': 'failed', 'platform': platform, 'error': str(e)})
                
        return results

    async def run_platform(self, platform, limit_per_alert=10):
        """Run autopilot for a specific platform"""
        platform = platform.lower()
        logger.info(f"Starting Autopilot for {platform} (User: {self.user_id})")
        
        # 1. Get Credentials
        creds = self._get_credentials(platform)
        if not creds:
            return {'success': False, 'message': f'Credentials for {platform} not found'}
            
        # 2. Get Alerts
        alerts = JobAlert.query.filter(
            JobAlert.user_id == self.user_id,
            JobAlert.is_active == True,
            JobAlert.platforms.ilike(f'%{platform}%')
        ).all()
        
        if not alerts:
            # Fallback to general alerts or profile
            profile = UserProfile.query.filter_by(user_id=self.user_id).first()
            if profile and profile.preferred_roles:
                # Create a default alert based on profile
                default_alert = JobAlert(
                    user_id=self.user_id,
                    name=f"Autopilot ({platform.capitalize()}): {profile.preferred_roles.split(',')[0].strip()}",
                    keywords=profile.preferred_roles,
                    location=profile.preferred_locations or 'Remote',
                    platforms=platform.capitalize(),
                    is_active=True
                )
                db.session.add(default_alert)
                db.session.commit()
                alerts = [default_alert]
                logger.info(f"Autopilot: Created default alert for user {self.user_id} based on profile for {platform}.")
            else:
                return {'success': False, 'message': f'No job alerts found for {platform}. Please create a Job Alert or fill your Discovery Preferences first.'}

        results = {'jobs_scraped': 0, 'applications_sent': 0, 'details': []}
        
        # Get user schedule and matching engine
        schedule = Schedule.query.filter_by(user_id=self.user_id).first()
        threshold = schedule.match_threshold if schedule else 70
        daily_limit = schedule.daily_limit if schedule else 5
        
        user_profile = UserProfile.query.filter_by(user_id=self.user_id).first()
        if not user_profile:
            logger.warning(f"Autopilot: No profile found for user {self.user_id}, skipping applications for {platform}.")
            # Continue to scrape, but won't apply
            
        engine = MatchingEngine(user_profile) if user_profile else None
        
        # Check today's application count
        today_apps = Application.query.filter(
            Application.user_id == self.user_id,
            Application.applied_at >= date.today()
        ).count()

        # 3. Initialize Scraper
        try:
            async with ScraperFactory.get_scraper(platform, headless=True) as scraper:
                # Load cookies for LinkedIn
                import json
                if platform == 'linkedin' and hasattr(creds, 'session_cookies') and creds.session_cookies:
                    try:
                        cookies = json.loads(creds.session_cookies)
                        await scraper.set_cookies(cookies)
                    except Exception as cookie_err:
                        logger.error(f"Autopilot: Error loading LinkedIn cookies: {str(cookie_err)}")

                login_success = await scraper.login(creds.email, creds.get_password())
                if not login_success:
                    logger.warning(f"{platform.capitalize()} login failed for user {self.user_id}. Proceeding as guest if possible.")
                else:
                    logger.info(f"{platform.capitalize()} login successful for user {self.user_id}")
                    # Save cookies for LinkedIn after successful login
                    if platform == 'linkedin':
                        try:
                            new_cookies = await scraper.get_cookies()
                            creds.session_cookies = json.dumps(new_cookies)
                            creds.last_login = datetime.utcnow()
                            db.session.commit()
                            logger.info(f"Autopilot: Saved LinkedIn cookies for user {self.user_id}")
                        except Exception as cookie_err:
                            logger.error(f"Autopilot: Error saving LinkedIn cookies: {str(cookie_err)}")
                            db.session.rollback()
                
                # Resume pre-check before auto-apply cycle
                resume_service = ResumeService(self.user_id)
                primary_resume = Resume.query.filter_by(user_id=self.user_id, is_primary=True).first()
                if not primary_resume:
                    logger.warning(f"Autopilot: No primary resume for user {self.user_id}. Attempting to use latest.")
                    primary_resume = Resume.query.filter_by(user_id=self.user_id).order_by(Resume.created_at.desc()).first()
                
                if not primary_resume:
                    logger.error(f"Autopilot: Resume pre-check failed. No resume found for user {self.user_id}.")
                    results['details'].append({'status': 'failed', 'platform': platform, 'error': 'No resume found. Please upload or generate a resume.'})
                    return results # Exit platform run
                
                # Abort if validation fails
                try:
                    resume_json = json.loads(primary_resume.content_json) if primary_resume.content_json else {}
                    is_valid, validation_msg = resume_service.validator.validate_all(resume_json)
                    if not is_valid:
                         logger.error(f"Autopilot: Resume validation failed for user {self.user_id}: {validation_msg}")
                         results['details'].append({'status': 'failed', 'platform': platform, 'error': f'Resume Validation Failed: {validation_msg}'})
                         return results
                except Exception as val_err:
                    logger.warning(f"Autopilot: Error during resume validation: {str(val_err)}. Proceeding with caution.")

                for alert in alerts:
                    logger.info(f"Autopilot ({platform}): Processing alert '{alert.name}'")
                    
                    jobs = await scraper.search_jobs(
                        keywords=alert.keywords,
                        location=alert.location,
                        easy_apply_only=(platform == 'linkedin'), # Only LinkedIn has explicit easy apply filter
                        limit=limit_per_alert
                    )
                    
                    saved_count = scraper.save_jobs_to_db(jobs)
                    # Safety check for misconfigured mocks or unexpected returns
                    if isinstance(saved_count, (int, float)):
                        results['jobs_scraped'] += int(saved_count)
                    
                    logger.info(f"Autopilot ({platform}): Scraped {len(jobs)} jobs, {saved_count} were new.")
                    
                    # Apply logic (specific to platform or generic)
                    if platform in ['linkedin', 'naukri'] and user_profile:
                        for job_data in jobs:
                            if today_apps >= daily_limit:
                                logger.info(f"Autopilot ({platform}): Daily limit of {daily_limit} reached for user {self.user_id}")
                                break
                                
                            db_job = JobPost.query.filter_by(job_url=job_data['job_url']).first()
                            if not db_job: continue
                            
                            # Check if already applied
                            existing_app = Application.query.filter(
                                Application.user_id == self.user_id,
                                Application.job_id == db_job.id
                            ).first()
                            
                            if existing_app:
                                logger.info(f"Autopilot ({platform}): Skipping {db_job.title} - already applied.")
                                continue
                            
                            # Calculate match score
                            score = engine.calculate_score(db_job)
                            
                            if score < threshold:
                                logger.info(f"Autopilot ({platform}): Skipping {db_job.title} - Score {score}% < Threshold {threshold}%")
                                continue
                                
                            logger.info(f"Autopilot ({platform}): Applying to job {db_job.title} at {db_job.company} (Score: {score}%)")
                            
                            # Add a human-like delay between applications
                            delay = random.uniform(5, 15)
                            logger.info(f"Autopilot ({platform}): Waiting {delay:.1f}s to mimic human behavior...")
                            await asyncio.sleep(delay)
                            
                            # Attach best resume version automatically
                            best_resume_path, res_type = await resume_service.get_best_resume_for_job(db_job.id)
                            logger.info(f"Autopilot ({platform}): Using {res_type} resume for {db_job.title}.")

                            apply_res = {'success': False, 'message': 'No applier for this platform'}
                            if platform == 'linkedin':
                                apply_res = await apply_to_linkedin_job(self.user_id, db_job.id, resume_path=best_resume_path)
                            elif platform == 'naukri':
                                apply_res = await apply_to_naukri_job(self.user_id, db_job.id, resume_path=best_resume_path)
                                
                            if apply_res['success']:
                                results['applications_sent'] += 1
                                today_apps += 1
                                results['details'].append({
                                    'status': 'success',
                                    'job': db_job.title,
                                    'company': db_job.company,
                                    'platform': platform,
                                    'score': score
                                })
                            else:
                                results['details'].append({
                                    'status': 'failed',
                                    'job': db_job.title,
                                    'company': db_job.company,
                                    'platform': platform,
                                    'error': apply_res.get('message', 'Unknown error')
                                })
                    else:
                        for job_data in jobs[:5]: # Log a few scraped jobs even if not applying
                            results['details'].append({'status': 'scraped', 'job': job_data['title'], 'platform': platform})

            return results
        except Exception as e:
            logger.error(f"{platform.capitalize()} automation error: {str(e)}")
            return {'success': False, 'message': str(e), 'jobs_scraped': results['jobs_scraped']}

    def _get_credentials(self, platform):
        """Helper to get credentials for any platform"""
        if platform == 'linkedin':
            return LinkedInCredentials.query.filter_by(user_id=self.user_id, is_active=True).first()
        elif platform == 'naukri':
            return NaukriCredentials.query.filter_by(user_id=self.user_id, is_active=True).first()
        else:
            return PlatformCredential.query.filter_by(user_id=self.user_id, platform=platform, is_active=True).first()

    # Legacy method names for compatibility
    async def run_naukri(self, limit_per_alert=10):
        return await self.run_platform('naukri', limit_per_alert)

    async def run_naukri_quick_apply(self, limit=10):
        # Specific implementation for bulk apply
        # Keeping existing logic but using run_platform internally or similar
        return await self._run_naukri_bulk(limit)

    async def _run_naukri_bulk(self, limit):
        # Re-copying the quick apply logic here for now to avoid breakage
        # (The logic from step 537)
        credentials = NaukriCredentials.query.filter_by(user_id=self.user_id, is_active=True).first()
        if not credentials: return {'success': False, 'message': 'Naukri credentials not found'}
        
        results = {'jobs_scraped': 0, 'applications_sent': 0, 'details': [], 'searches': []}
        
        profile = UserProfile.query.filter_by(user_id=self.user_id).first()
        if not profile or not profile.preferred_roles:
            return {'success': False, 'message': 'No search keywords found in profile'}
            
        keywords = profile.preferred_roles
        location = profile.preferred_locations or ''

        async with ScraperFactory.get_scraper('naukri', headless=False) as scraper:
            login_success = await scraper.login(credentials.email, credentials.get_password())
            if not login_success:
                logger.warning(f"Naukri login failed for user {self.user_id} during quick apply. Proceeding as guest.")
            
            logger.info(f"Naukri Quick Apply: Searching for '{keywords}' in '{location}'...")
            results['searches'].append({'keywords': keywords, 'location': location})
            jobs = await scraper.search_jobs(keywords=keywords, location=location, limit=limit)
            
            scraper.save_jobs_to_db(jobs)
            results['jobs_scraped'] = len(jobs)
            logger.info(f"Naukri Quick Apply: Scraped {len(jobs)} jobs.")
            
            # Resume check for bulk apply
            resume_service = ResumeService(self.user_id)
            
            for job_data in jobs:
                if results['applications_sent'] >= limit: break
                
                db_job = JobPost.query.filter_by(job_url=job_data['job_url']).first()
                if not db_job: continue
                
                # Check if already applied
                existing_app = Application.query.filter_by(user_id=self.user_id, job_id=db_job.id).first()
                if existing_app: 
                    logger.info(f"Skipping {db_job.title} - already applied.")
                    continue
                
                # Attach best resume version
                best_resume_path, res_type = await resume_service.get_best_resume_for_job(db_job.id)
                logger.info(f"Naukri Quick Apply: Using {res_type} resume for {db_job.title}.")

                logger.info(f"Naukri Quick Apply: Applying to {db_job.title}...")
                apply_res = await apply_to_naukri_job(self.user_id, db_job.id, resume_path=best_resume_path)
                
                if apply_res['success']:
                    results['applications_sent'] += 1
                    results['details'].append({'status': 'success', 'job': db_job.title, 'company': db_job.company})
                else:
                    results['details'].append({'status': 'failed', 'job': db_job.title, 'company': db_job.company, 'error': apply_res.get('message', 'Unknown error')})
                
                await asyncio.sleep(random.uniform(5, 10))
                    
        return results

# Keep Alias for backward compatibility
LinkedInAutopilot = Autopilot

async def run_linkedin_autopilot(user_id):
    """Execution wrapper for LinkedIn Autopilot"""
    ap = Autopilot(user_id)
    return await ap.run_platform('linkedin')

async def run_naukri_autopilot(user_id):
    """Execution wrapper for Naukri Autopilot"""
    ap = Autopilot(user_id)
    return await ap.run_platform('naukri')

async def run_naukri_quick_apply_task(user_id, limit=10):
    """Execution wrapper for Naukri Quick Apply"""
    ap = Autopilot(user_id)
    return await ap.run_naukri_quick_apply(limit=limit)

async def run_autopilot(user_id):
    """Run all autopilot tasks for a user"""
    ap = Autopilot(user_id)
    return await ap.run()
