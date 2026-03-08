"""
Job Alerts Routes

Handles job alert management, creation, editing, and testing.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import JobAlert, User
from app.services.job_alerts import JobAlertsService
from app.services.matching import update_matches_for_user
from app import db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('alerts', __name__, url_prefix='/alerts')


@bp.route('/', methods=['GET'])
@login_required
def index():
    """List all job alerts"""
    alerts = JobAlert.query.filter_by(user_id=current_user.id).order_by(JobAlert.created_at.desc()).all()
    
    # Get stats
    active_alerts = sum(1 for alert in alerts if alert.is_active)
    total_alerts = len(alerts)
    
    return render_template('alerts/index.html', 
                         alerts=alerts,
                         active_alerts=active_alerts,
                         total_alerts=total_alerts)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new job alert"""
    
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            keywords = request.form.get('keywords')
            location = request.form.get('location', '')
            platforms = request.form.getlist('platforms')  # Multiple checkboxes
            frequency = request.form.get('frequency', 'instant')
            email_enabled = request.form.get('email_enabled') == 'on'
            
            # Validation
            if not name or not keywords:
                flash('Alert name and keywords are required', 'danger')
                return redirect(url_for('alerts.create'))
            
            # Create alert
            alert = JobAlert(
                user_id=current_user.id,
                name=name,
                keywords=keywords,
                location=location,
                platforms=','.join(platforms) if platforms else '',
                frequency=frequency,
                email_enabled=email_enabled,
                is_active=True
            )
            
            db.session.add(alert)
            db.session.commit()
            
            # Update matches to reflect new alert keywords
            update_matches_for_user(current_user.id)
            
            flash(f'Job alert "{name}" created successfully!', 'success')
            return redirect(url_for('alerts.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating alert: {str(e)}")
            flash(f'Error creating alert: {str(e)}', 'danger')
            return redirect(url_for('alerts.create'))
    
    return render_template('alerts/create.html')


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit a job alert"""
    alert = JobAlert.query.get_or_404(id)
    
    # Check ownership
    if alert.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('alerts.index'))
    
    if request.method == 'POST':
        try:
            # Update alert
            alert.name = request.form.get('name')
            alert.keywords = request.form.get('keywords')
            alert.location = request.form.get('location', '')
            platforms = request.form.getlist('platforms')
            alert.platforms = ','.join(platforms) if platforms else ''
            alert.frequency = request.form.get('frequency', 'instant')
            alert.email_enabled = request.form.get('email_enabled') == 'on'
            alert.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Update matches to reflect changes
            update_matches_for_user(current_user.id)
            
            flash(f'Alert "{alert.name}" updated successfully!', 'success')
            return redirect(url_for('alerts.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating alert: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('alerts.edit', id=id))
    
    # Parse platforms for display
    alert.platforms_list = alert.platforms.split(',') if alert.platforms else []
    
    return render_template('alerts/edit.html', alert=alert)


@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete a job alert"""
    alert = JobAlert.query.get_or_404(id)
    
    # Check ownership
    if alert.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('alerts.index'))
    
    try:
        alert_name = alert.name
        db.session.delete(alert)
        db.session.commit()
        flash(f'Alert "{alert_name}" deleted', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting alert: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('alerts.index'))


@bp.route('/toggle/<int:id>', methods=['POST'])
@login_required
def toggle(id):
    """Toggle alert active status"""
    alert = JobAlert.query.get_or_404(id)
    
    # Check ownership
    if alert.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        alert.is_active = not alert.is_active
        alert.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = 'enabled' if alert.is_active else 'disabled'
        return jsonify({
            'success': True,
            'message': f'Alert {status}',
            'is_active': alert.is_active
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling alert: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/test/<int:id>', methods=['POST'])
@login_required
def test(id):
    """Test a job alert"""
    alert = JobAlert.query.get_or_404(id)
    
    # Check ownership
    if alert.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Check for matching jobs
        service = JobAlertsService()
        
        alert_config = {
            'keywords': alert.keywords,
            'location': alert.location,
            'platforms': alert.platforms.split(',') if alert.platforms else [],
            'last_checked': alert.last_checked
        }
        
        jobs = service.check_for_new_jobs(alert_config)
        
        # Send test email if jobs found
        if jobs and alert.email_enabled:
            user = User.query.get(current_user.id)
            user_name = user.email.split('@')[0]  # Use email prefix as name
            
            service.send_job_alert(
                user_email=user.email,
                user_name=user_name,
                jobs=jobs,
                alert_name=alert.name
            )
            
            return jsonify({
                'success': True,
                'message': f'Found {len(jobs)} matching jobs! Test email sent.',
                'job_count': len(jobs)
            })
        elif jobs:
            return jsonify({
                'success': True,
                'message': f'Found {len(jobs)} matching jobs! (Email disabled)',
                'job_count': len(jobs)
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No matching jobs found at this time.',
                'job_count': 0
            })
            
    except Exception as e:
        logger.error(f"Error testing alert: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/unsubscribe', methods=['GET', 'POST'])
@login_required
def unsubscribe():
    """Unsubscribe from all alerts"""
    
    if request.method == 'POST':
        try:
            # Disable all alerts
            alerts = JobAlert.query.filter_by(user_id=current_user.id).all()
            
            for alert in alerts:
                alert.is_active = False
                alert.email_enabled = False
            
            db.session.commit()
            
            flash('You have been unsubscribed from all job alerts', 'success')
            return redirect(url_for('alerts.index'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error unsubscribing: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('alerts.unsubscribe'))
    
    # Get alert count
    alert_count = JobAlert.query.filter_by(user_id=current_user.id, is_active=True).count()
    
    return render_template('alerts/unsubscribe.html', alert_count=alert_count)
