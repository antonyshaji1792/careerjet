"""
Naukri.com Integration Routes

Handles Naukri credential management, job scraping, and application automation.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import NaukriCredentials, NaukriJob, JobPost, UserProfile
from app.utils.rate_limiter import rate_limit
from app.utils.credit_middleware import credit_required
from app import db

import asyncio
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('naukri', __name__, url_prefix='/naukri')

@bp.route('/', methods=['GET'])
@login_required
def index():
    """Naukri integration dashboard"""
    credentials = NaukriCredentials.query.filter_by(user_id=current_user.id).first()
    
    # Get Naukri job stats
    naukri_jobs_count = NaukriJob.query.filter_by(is_active=True).count()
    
    # Get alert stats for Naukri
    from app.models import JobAlert
    alerts_count = JobAlert.query.filter(
        JobAlert.user_id == current_user.id,
        JobAlert.is_active == True,
        JobAlert.platforms.ilike('%naukri%')
    ).count()
    
    # Get schedule/autopilot status
    from app.models import Schedule
    schedule = Schedule.query.filter_by(user_id=current_user.id).first()
    
    return render_template('naukri/index.html',
                         credentials=credentials,
                         naukri_jobs_count=naukri_jobs_count,
                         alerts_count=alerts_count,
                         schedule=schedule)

@bp.route('/credentials', methods=['GET', 'POST'])
@login_required
def credentials():
    """Manage Naukri credentials"""
    credentials = NaukriCredentials.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Email and password are required', 'danger')
            return redirect(url_for('naukri.credentials'))
        
        try:
            if credentials:
                credentials.email = email
                credentials.set_password(password)
                credentials.is_active = True
            else:
                credentials = NaukriCredentials(
                    user_id=current_user.id,
                    email=email,
                    is_active=True
                )
                credentials.set_password(password)
                db.session.add(credentials)
            
            db.session.commit()
            flash('Naukri credentials saved successfully!', 'success')
            return redirect(url_for('naukri.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving Naukri credentials: {str(e)}")
            flash(f'Error saving credentials: {str(e)}', 'danger')
            return redirect(url_for('naukri.credentials'))
    
    return render_template('naukri/credentials.html', credentials=credentials)

@bp.route('/scrape', methods=['POST'])
@login_required
@rate_limit(limit=2, period=300) # Once every 3 mins approx
def scrape_jobs():

    """Trigger Naukri job scraping"""
    try:
        keywords = request.form.get('keywords', '')
        location = request.form.get('location', '')
        limit = int(request.form.get('limit', 25))
        
        if not keywords:
            flash('Please enter job search keywords', 'warning')
            return redirect(url_for('naukri.index'))
        
        from app.services.naukri_scraper import scrape_naukri_jobs
        
        # Run scraping
        result = asyncio.run(scrape_naukri_jobs(
            user_id=current_user.id,
            keywords=keywords,
            location=location,
            limit=limit
        ))
        
        if result['success']:
            # Trigger match update
            try:
                from app.services.matching import update_matches_for_user
                update_matches_for_user(current_user.id)
            except Exception as match_err:
                logger.error(f"Post-scrape matching error: {str(match_err)}")
                
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'danger')
        
        return redirect(url_for('naukri.jobs'))
        
    except Exception as e:
        logger.error(f"Naukri scraping error: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('naukri.index'))

@bp.route('/jobs', methods=['GET'])
@login_required
def jobs():
    """View Naukri jobs with match scores"""
    from app.models import JobMatch, JobPost
    
    naukri_jobs = NaukriJob.query.filter_by(is_active=True).order_by(NaukriJob.scraped_at.desc()).limit(100).all()
    
    results = []
    for job in naukri_jobs:
        match = JobMatch.query.join(JobPost).filter(
            JobMatch.user_id == current_user.id,
            JobPost.job_url == job.job_url
        ).first()
        
        results.append({
            'data': job,
            'match_score': match.match_score if match else None
        })
    
    return render_template('naukri/jobs.html', jobs=results)

@bp.route('/apply/<int:job_id>', methods=['POST'])
@login_required
@rate_limit(limit=10, period=60)
@credit_required('auto_apply')
def apply_to_job(job_id):

    """Apply to a Naukri job"""
    try:
        naukri_job = NaukriJob.query.get(job_id)
        if not naukri_job:
            return jsonify({'success': False, 'message': 'Job not found'}), 404
        
        from app.models import Application
        job_post = JobPost.query.filter_by(job_url=naukri_job.job_url).first()
        
        if not job_post:
            return jsonify({'success': False, 'message': 'Job post not found in database'}), 404
            
        from app.services.naukri_bot import apply_to_naukri_job
        result = asyncio.run(apply_to_naukri_job(current_user.id, job_post.id))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Naukri apply error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500
@bp.route('/test-connection', methods=['POST'])
@login_required
def test_connection():
    """Test Naukri connection"""
    try:
        credentials = NaukriCredentials.query.filter_by(
            user_id=current_user.id,
            is_active=True
        ).first()
        
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'No credentials found'
            })
        
        from app.services.naukri_scraper import NaukriScraper
        
        async def test_login():
            async with NaukriScraper(headless=False) as scraper:
                email = credentials.email
                password = credentials.get_password()
                success = await scraper.login(email, password)
                return success
        
        success = asyncio.run(test_login())
        
        if success:
            credentials.last_login = db.func.now()
            db.session.commit()
            return jsonify({'success': True, 'message': 'Naukri connection successful!'})
        else:
            return jsonify({'success': False, 'message': 'Naukri login failed. Please check your credentials.'})
            
    except Exception as e:
        logger.error(f"Naukri test connection error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@bp.route('/autopilot/run', methods=['POST'])
@login_required
@rate_limit(limit=1, period=1800) # Once every 30 mins
@credit_required('auto_apply')
def run_autopilot():

    """Run Naukri autopilot (scrape and apply)"""
    try:
        from app.services.autopilot import run_naukri_autopilot
        from app.models import Schedule
        from datetime import datetime
        
        # Update last run timestamp
        schedule = Schedule.query.filter_by(user_id=current_user.id).first()
        if schedule:
            schedule.last_run_at = datetime.utcnow()
            db.session.commit()
            
        result = asyncio.run(run_naukri_autopilot(current_user.id))
        
        if result.get('success', True): # run_naukri returns results dict directly
            return jsonify({
                'success': True,
                'message': f"Autopilot finished! Scraped {result['jobs_scraped']} jobs and sent {result['applications_sent']} applications.",
                'data': result
            })
        else:
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Naukri autopilot route error: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
@bp.route('/quick-apply', methods=['POST'])
@login_required
@rate_limit(limit=1, period=1800)
@credit_required('auto_apply')
def quick_apply():

    """Run Naukri Quick Apply (Apply to top 10 without matching)"""
    try:
        from app.services.autopilot import run_naukri_quick_apply_task
        from app.models import Schedule
        from datetime import datetime
        
        # Update last run timestamp
        schedule = Schedule.query.filter_by(user_id=current_user.id).first()
        if schedule:
            schedule.last_run_at = datetime.utcnow()
            db.session.commit()
            
        result = asyncio.run(run_naukri_quick_apply_task(current_user.id, limit=10))
        
        return jsonify({
            'success': True,
            'message': f"Quick Apply finished! Scraped {result['jobs_scraped']} jobs and applied to {result['applications_sent']}.",
            'data': result
        })
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Naukri quick apply route error: {str(e)}\n{error_details}")
        return jsonify({
            'success': False, 
            'message': f'Server Error: {str(e)}',
            'details': error_details
        }), 500
