"""
LinkedIn Integration Routes

Handles LinkedIn credential management, job scraping, and Easy Apply automation.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import LinkedInCredentials, LinkedInJob, JobPost, UserProfile
from app import db
import asyncio
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('linkedin', __name__, url_prefix='/linkedin')


@bp.route('/', methods=['GET'])
@login_required
def index():
    """LinkedIn integration dashboard"""
    credentials = LinkedInCredentials.query.filter_by(user_id=current_user.id).first()
    
    # Get LinkedIn job stats
    linkedin_jobs_count = LinkedInJob.query.filter_by(is_active=True).count()
    easy_apply_count = LinkedInJob.query.filter_by(is_easy_apply=True, is_active=True).count()
    
    # Get alert stats
    from app.models import JobAlert, Schedule
    alerts_count = JobAlert.query.filter_by(user_id=current_user.id, is_active=True).count()
    
    # Get schedule/autopilot status
    schedule = Schedule.query.filter_by(user_id=current_user.id).first()
    
    return render_template('linkedin/index.html',
                         credentials=credentials,
                         linkedin_jobs_count=linkedin_jobs_count,
                         easy_apply_count=easy_apply_count,
                         alerts_count=alerts_count,
                         schedule=schedule)


@bp.route('/credentials', methods=['GET', 'POST'])
@login_required
def credentials():
    """Manage LinkedIn credentials"""
    credentials = LinkedInCredentials.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required', 'danger')
            return redirect(url_for('linkedin.credentials'))
        
        try:
            if credentials:
                # Update existing credentials
                credentials.email = email
                credentials.set_password(password)
                credentials.is_active = True
            else:
                # Create new credentials
                credentials = LinkedInCredentials(
                    user_id=current_user.id,
                    email=email,
                    is_active=True
                )
                credentials.set_password(password)
                db.session.add(credentials)
            
            db.session.commit()
            flash('LinkedIn credentials saved successfully!', 'success')
            return redirect(url_for('linkedin.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving credentials: {str(e)}")
            flash(f'Error saving credentials: {str(e)}', 'danger')
            return redirect(url_for('linkedin.credentials'))
    
    return render_template('linkedin/credentials.html', credentials=credentials)


@bp.route('/credentials/delete', methods=['POST'])
@login_required
def delete_credentials():
    """Delete LinkedIn credentials"""
    credentials = LinkedInCredentials.query.filter_by(user_id=current_user.id).first()
    
    if credentials:
        db.session.delete(credentials)
        db.session.commit()
        flash('LinkedIn credentials deleted', 'success')
    
    return redirect(url_for('linkedin.index'))


@bp.route('/scrape', methods=['POST'])
@login_required
def scrape_jobs():
    """Trigger LinkedIn job scraping"""
    try:
        # Get search parameters
        keywords = request.form.get('keywords', '')
        location = request.form.get('location', '')
        limit = int(request.form.get('limit', 25))
        
        if not keywords:
            flash('Please enter job search keywords', 'warning')
            return redirect(url_for('linkedin.index'))
        
        # Check if credentials exist
        credentials = LinkedInCredentials.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not credentials:
            flash('Please add your LinkedIn credentials first', 'warning')
            return redirect(url_for('linkedin.credentials'))
        
        # Import scraper
        from app.services.linkedin_scraper import scrape_linkedin_jobs
        
        # Run scraping in background (in production, use Celery)
        # For now, we'll run it synchronously
        result = asyncio.run(scrape_linkedin_jobs(
            user_id=current_user.id,
            keywords=keywords,
            location=location,
            limit=limit
        ))
        
        if result['success']:
            # Trigger match update so scores show up immediately
            try:
                from app.services.matching import update_matches_for_user
                update_matches_for_user(current_user.id)
            except Exception as match_err:
                logger.error(f"Post-scrape matching error: {str(match_err)}")
                
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'danger')
        
        return redirect(url_for('linkedin.jobs'))
        
    except Exception as e:
        logger.error(f"Scraping error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('linkedin.index'))


@bp.route('/jobs', methods=['GET'])
@login_required
def jobs():
    """View LinkedIn jobs with match scores and application status"""
    from app.models import JobMatch, JobPost, Application
    
    # Get filter parameters
    easy_apply_only = request.args.get('easy_apply', 'true') == 'true'
    show_applied = request.args.get('show_applied', 'false') == 'true'
    
    # Query LinkedIn jobs
    query = LinkedInJob.query.filter_by(is_active=True)
    if easy_apply_only:
        query = query.filter_by(is_easy_apply=True)
    
    # We need to filter by application status if requested
    # This requires reaching into JobPost and Application tables
    all_jobs = query.order_by(LinkedInJob.scraped_at.desc()).all()
    
    results = []
    for job in all_jobs:
        # Find corresponding JobPost
        job_post = JobPost.query.filter_by(job_url=job.job_url).first()
        
        match_score = None
        app_status = None
        
        if job_post:
            # Get match score
            match = JobMatch.query.filter_by(user_id=current_user.id, job_id=job_post.id).first()
            if match:
                match_score = match.match_score
            
            # Get application status
            app = Application.query.filter_by(user_id=current_user.id, job_id=job_post.id).first()
            if app:
                app_status = app.status

        # Filter based on tab selection
        if show_applied:
            if not app_status or app_status.lower() != 'applied':
                continue
        else:
            if app_status and app_status.lower() == 'applied':
                continue

        results.append({
            'data': job,
            'match_score': match_score,
            'app_status': app_status
        })
    
    return render_template('linkedin/jobs.html', 
                         jobs=results[:100], 
                         easy_apply_only=easy_apply_only,
                         show_applied=show_applied)


@bp.route('/apply/<int:job_id>', methods=['POST'])
@login_required
def apply_to_job(job_id):
    """Apply to a LinkedIn job using Celery background task"""
    from app.models import Application
    try:
        # Get job
        linkedin_job = LinkedInJob.query.get(job_id)
        if not linkedin_job:
            return jsonify({'success': False, 'message': 'Job not found'}), 404
            
        # Find corresponding JobPost
        job_post = JobPost.query.filter_by(job_url=linkedin_job.job_url).first()
        if not job_post:
             return jsonify({'success': False, 'message': 'Job post not found in database'}), 404

        # Check if already applied
        existing_application = Application.query.filter_by(
            user_id=current_user.id,
            job_id=job_post.id
        ).first()
        
        if existing_application and existing_application.status in ['Applied', 'Processing']:
             return jsonify({
                'success': False,
                'message': f'Application already in state: {existing_application.status}',
                'application_id': existing_application.id
            }), 400

        # Create or reuse application record
        if existing_application:
            application = existing_application
            application.status = 'Processing'
            application.status_message = 'Starting background application...'
            application.error_message = None
            application.screenshot_path = None
            application.applied_at = None
        else:
            application = Application(
                user_id=current_user.id,
                job_id=job_post.id,
                status='Processing',
                status_message='Starting background application...'
            )
            db.session.add(application)
        
        db.session.commit()
        
        # Trigger Celery task
        from app.tasks.celery_tasks import apply_to_linkedin_job_task
        apply_to_linkedin_job_task.delay(current_user.id, job_post.id, application.id)
        
        return jsonify({
            'success': True,
            'message': 'Application started in background',
            'application_id': application.id
        })

    except Exception as e:
        logger.error(f"Apply error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@bp.route('/application-status/<int:application_id>')
@login_required
def application_status(application_id):
    """Check the status of a background application"""
    from app.models import Application
    application = Application.query.get_or_404(application_id)
    
    # Security check
    if application.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    return jsonify({
        'status': application.status,
        'message': application.status_message,
        'error': application.error_message,
        'screenshot': f'/uploads/screenshots/{application.screenshot_path}' if application.screenshot_path else None
    })


@bp.route('/test-connection', methods=['POST'])
@login_required
def test_connection():
    """Test LinkedIn connection"""
    try:
        credentials = LinkedInCredentials.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No credentials found'
            })
        
        # Import scraper for testing
        from app.services.linkedin_scraper import LinkedInScraper
        
        async def test_login():
            async with LinkedInScraper(headless=False) as scraper:
                # Load cookies if available
                import json
                if credentials.session_cookies:
                    try:
                        cookies = json.loads(credentials.session_cookies)
                        await scraper.set_cookies(cookies)
                    except Exception as e:
                        logger.error(f"Test connection: Error loading cookies: {str(e)}")

                email = credentials.email
                password = credentials.get_password()
                success = await scraper.login(email, password)
                
                # Save cookies after successful login
                if success:
                    try:
                        new_cookies = await scraper.get_cookies()
                        credentials.session_cookies = json.dumps(new_cookies)
                        credentials.last_login = db.func.now()
                        db.session.commit()
                    except Exception as e:
                        logger.error(f"Test connection: Error saving cookies: {str(e)}")
                        db.session.rollback()
                        
                return success
        
        success = asyncio.run(test_login())
        
        if success:
            credentials.last_login = db.func.now()
            db.session.commit()
            
            message = 'LinkedIn connection successful!'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({'success': True, 'message': message})
            
            flash(message, 'success')
            return redirect(url_for('linkedin.index'))
        else:
            message = 'LinkedIn login failed. Please check your credentials.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or 'application/json' in request.headers.get('Accept', ''):
                return jsonify({'success': False, 'message': message})
            
            flash(message, 'danger')
            return redirect(url_for('linkedin.index'))
            
    except Exception as e:
        logger.error(f"Test connection error: {str(e)}")
        message = f'Error: {str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json or 'application/json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'message': message})
        
        flash(message, 'danger')
        return redirect(url_for('linkedin.index'))


@bp.route('/autopilot/run', methods=['POST'])
@login_required
def run_autopilot():
    """Run LinkedIn autopilot (scrape and apply)"""
    try:
        from app.services.autopilot import run_linkedin_autopilot
        from app.models import Schedule
        from datetime import datetime
        
        # Update last run timestamp
        schedule = Schedule.query.filter_by(user_id=current_user.id).first()
        if schedule:
            schedule.last_run_at = datetime.utcnow()
            db.session.commit()
            
        # Run autopilot in background (or synchronously for now)
        result = asyncio.run(run_linkedin_autopilot(current_user.id))
        
        if result['success']:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify(result)
            flash(result['message'], 'success')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify(result)
            flash(result['message'], 'danger')
            
        return redirect(url_for('linkedin.index'))
        
    except Exception as e:
        logger.error(f"Autopilot route error: {str(e)}")
        message = f'Error: {str(e)}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': False, 'message': message})
        flash(message, 'danger')
        return redirect(url_for('linkedin.index'))
