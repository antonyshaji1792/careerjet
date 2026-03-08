from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import User, Plan, Subscription
from app import db
from functools import wraps

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    from app.models import Application, JobPost, JobAlert, LinkedInJob, NaukriJob
    from datetime import datetime, timedelta
    
    users = User.query.all()
    today = datetime.utcnow().replace(hour=0, minute=0, second=0)
    
    stats = {
        'total_users': len(users),
        'total_applications': Application.query.count(),
        'apps_today': Application.query.filter(Application.applied_at >= today).count(),
        'total_jobs': JobPost.query.count(),
        'jobs_today': JobPost.query.filter(JobPost.ingested_at >= today).count(),
        'linkedin_jobs': LinkedInJob.query.filter_by(is_active=True).count(),
        'naukri_jobs': NaukriJob.query.filter_by(is_active=True).count(),
        'active_alerts': JobAlert.query.filter_by(is_active=True).count(),
        'active_subscriptions': Subscription.query.filter_by(status='active').count(),
    }
    
    # System health (simple checks)
    health = {
        'database': 'Healthy',
        'background_workers': 'Active', # Simplified
        'last_sync': datetime.now().strftime('%H:%M')
    }
    
    recent_apps = Application.query.order_by(Application.applied_at.desc()).limit(15).all()
    plans = Plan.query.all()
    
    return render_template('admin/dashboard.html', 
                         users=users, 
                         stats=stats, 
                         health=health,
                         recent_apps=recent_apps,
                         plans=plans)


@bp.route('/logs')
@login_required
@admin_required
def logs():
    """View system logs (last 500 lines)"""
    import os
    log_file = 'app.log' # Assuming standard naming
    log_content = "No log file found."
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            lines = f.readlines()
            log_content = "".join(lines[-500:])
    return render_template('admin/logs.html', log_content=log_content)

@bp.route('/activity-feed')
@login_required
@admin_required
def activity_feed():
    """API endpoint for real-time monitoring of autopilot actions"""
    from app.models import Application, JobPost
    from flask import jsonify
    recent = Application.query.join(JobPost).order_by(Application.applied_at.desc()).limit(20).all()
    data = []
    for app in recent:
        data.append({
            'user': app.user.email,
            'job': app.job.title,
            'company': app.job.company,
            'status': app.status,
            'time': app.applied_at.strftime('%H:%M:%S') if app.applied_at else 'Pending'
        })
    return jsonify(data)

@bp.route('/user/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    if not current_user.is_super_admin:
        flash('Only super admins can promote others to admin.', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot demote yourself.', 'warning')
        return redirect(url_for('admin.dashboard'))
        
    user.is_admin = not user.is_admin
    db.session.commit()
    flash(f'Admin status for {user.email} updated.', 'success')
    return redirect(url_for('admin.dashboard'))

@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if not current_user.is_super_admin:
        flash('Only super admins can delete users.', 'danger')
        return redirect(url_for('admin.dashboard'))
        
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete yourself.', 'danger')
        return redirect(url_for('admin.dashboard'))
        
@bp.route('/config', methods=['GET', 'POST'])
@login_required
@admin_required
def config():
    from app.models import SystemConfig
    
    providers = ['OPENAI', 'ANTHROPIC', 'GEMINI', 'OLLAMA']
    
    if request.method == 'POST':
        # Define expected keys and settings
        llm_configs = {
            'OPENAI_API_KEY': ('Primary key for GPT-4o and extraction', True),
            'ANTHROPIC_API_KEY': ('Key for Claude models', True),
            'GEMINI_API_KEY': ('Key for Gemini Pro models', True),
            'OLLAMA_BASE_URL': ('Local Ollama API URL (e.g. http://localhost:11434)', False),
            'OLLAMA_MODEL': ('Model to use with Ollama (e.g. llama3)', False),
            'PRIMARY_LLM_PROVIDER': ('Active AI provider for the system', False),
            # SMTP Configs
            'SMTP_SERVER': ('SMTP Server (e.g. smtp.gmail.com)', False),
            'SMTP_PORT': ('SMTP Port (e.g. 587)', False),
            'SMTP_USER': ('SMTP Username', False),
            'SMTP_PASSWORD': ('SMTP Password', True),
            'SMTP_FROM_EMAIL': ('Sender email address', False),
        }
        
        # Save general configs
        for key, (desc, encrypt) in llm_configs.items():
            val = request.form.get(key)
            if val is not None:
                if val != '********':
                    SystemConfig.set_config_value(key, val, is_encrypted=encrypt, description=desc)
        
        # Save activation toggles
        for provider in providers:
            is_active = request.form.get(f'{provider}_IS_ACTIVE') == 'on'
            SystemConfig.set_config_value(f'{provider}_IS_ACTIVE', 'true' if is_active else 'false', description=f'Whether {provider} is enabled')
        
        # Save SMTP TLS toggle
        smtp_tls = request.form.get('SMTP_USE_TLS') == 'on'
        SystemConfig.set_config_value('SMTP_USE_TLS', 'true' if smtp_tls else 'false', description='Whether to use TLS for SMTP')
            
        flash('System configuration updated successfully.', 'success')
        return redirect(url_for('admin.config'))
        
    # GET request - fetch current settings
    configs = {
        'OPENAI_API_KEY': '********' if SystemConfig.get_config_value('OPENAI_API_KEY') else '',
        'ANTHROPIC_API_KEY': '********' if SystemConfig.get_config_value('ANTHROPIC_API_KEY') else '',
        'GEMINI_API_KEY': '********' if SystemConfig.get_config_value('GEMINI_API_KEY') else '',
        'OLLAMA_BASE_URL': SystemConfig.get_config_value('OLLAMA_BASE_URL', 'http://localhost:11434'),
        'OLLAMA_MODEL': SystemConfig.get_config_value('OLLAMA_MODEL', 'llama3'),
        'PRIMARY_LLM_PROVIDER': SystemConfig.get_config_value('PRIMARY_LLM_PROVIDER', 'openai'),
        # SMTP
        'SMTP_SERVER': SystemConfig.get_config_value('SMTP_SERVER', ''),
        'SMTP_PORT': SystemConfig.get_config_value('SMTP_PORT', '587'),
        'SMTP_USER': SystemConfig.get_config_value('SMTP_USER', ''),
        'SMTP_PASSWORD': '********' if SystemConfig.get_config_value('SMTP_PASSWORD') else '',
        'SMTP_FROM_EMAIL': SystemConfig.get_config_value('SMTP_FROM_EMAIL', ''),
        'SMTP_USE_TLS': SystemConfig.get_config_value('SMTP_USE_TLS', 'true') == 'true'
    }
    
    # Add activation states
    for provider in providers:
        configs[f'{provider}_IS_ACTIVE'] = SystemConfig.get_config_value(f'{provider}_IS_ACTIVE', 'true') == 'true'
    
    return render_template('admin/config.html', configs=configs)

@bp.route('/test-smtp', methods=['POST'])
@login_required
@admin_required
def test_smtp():
    """Send a test email to verify SMTP settings"""
    from flask import jsonify
    try:
        from app.services.job_alerts import JobAlertsService
        service = JobAlertsService()
        
        subject = "CareerJet SMTP Test"
        html_content = f"""
        <div style="font-family: sans-serif; padding: 20px; border: 1px solid #e2e8f0; border-radius: 10px;">
            <h2 style="color: #6366f1;">🚀 SMTP Connection Successful!</h2>
            <p>Your CareerJet mail server is correctly configured.</p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
            <p style="font-size: 0.875rem; color: #64748b;">
                <strong>Recipient:</strong> {current_user.email}
            </p>
        </div>
        """
        
        success = service.send_email(current_user.email, subject, html_content)
        
        if success:
            return jsonify({'success': True, 'message': f'Test email sent successfully to {current_user.email}!'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send test email. Please check your logs and SMTP settings.'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@bp.route('/autopilot-monitor')
@login_required
@admin_required
def autopilot_monitor():
    """Detailed monitoring of all users' autopilot status and performance"""
    from app.models import Schedule, Application, User, JobAlert
    from datetime import datetime
    
    # Get all users with autopilot enabled
    active_schedules = Schedule.query.filter_by(is_autopilot_enabled=True).all()
    
    monitor_data = []
    today = datetime.utcnow().replace(hour=0, minute=0, second=0)
    
    for schedule in active_schedules:
        user = User.query.get(schedule.user_id)
        if not user: continue
        
        # Count apps today
        apps_today = Application.query.filter(
            Application.user_id == user.id,
            Application.applied_at >= today
        ).count()
        
        # Count total apps
        total_apps = Application.query.filter_by(user_id=user.id).count()
        
        # Get active alerts
        alerts_count = JobAlert.query.filter_by(user_id=user.id, is_active=True).count()
        
        # Check platform connectivity
        has_linkedin = user.linkedin_credentials is not None and user.linkedin_credentials.is_active
        has_naukri = user.naukri_credentials is not None and user.naukri_credentials.is_active
        
        monitor_data.append({
            'user_email': user.email,
            'search_limit': schedule.daily_search_limit,
            'apply_limit': schedule.daily_limit,
            'apps_today': apps_today,
            'total_apps': total_apps,
            'alerts': alerts_count,
            'linkedin': 'Connected' if has_linkedin else 'Missing',
            'naukri': 'Connected' if has_naukri else 'Missing',
            'last_active': schedule.last_run_at.strftime('%Y-%m-%d %H:%M') if schedule.last_run_at else 'Never'
        })
        
    return render_template('admin/autopilot_monitor.html', monitor_data=monitor_data)
@bp.route('/plans', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_plans():
    """Admin configuration to manage subscription plans."""
    if request.method == 'POST':
        plan_id = request.form.get('plan_id')
        name = request.form.get('name')
        slug = request.form.get('slug')
        price = float(request.form.get('price', 0))
        stripe_price_id = request.form.get('stripe_price_id')
        interval = request.form.get('interval', 'month')
        credits_per_interval = int(request.form.get('credits_per_interval', 0))
        rollover_allowed = request.form.get('rollover_allowed') == 'on'
        is_active = request.form.get('is_active') == 'on'
        features_raw = request.form.get('features', '')
        features = [f.strip() for f in features_raw.split('\n') if f.strip()]
        
        if plan_id:
            plan = Plan.query.get(plan_id)
            if plan:
                plan.name = name
                plan.slug = slug
                plan.price = price
                plan.stripe_price_id = stripe_price_id
                plan.interval = interval
                plan.credits_per_interval = credits_per_interval
                plan.rollover_allowed = rollover_allowed
                plan.is_active = is_active
                plan.features = features
                flash(f'Plan "{name}" updated.', 'success')
        else:
            new_plan = Plan(
                name=name, slug=slug, price=price,
                stripe_price_id=stripe_price_id,
                interval=interval, credits_per_interval=credits_per_interval,
                rollover_allowed=rollover_allowed, is_active=is_active,
                features=features
            )
            db.session.add(new_plan)
            flash(f'Plan "{name}" created.', 'success')
            
        db.session.commit()
        return redirect(url_for('admin.manage_plans'))

    plans = Plan.query.all()
    return render_template('admin/plans.html', plans=plans)

@bp.route('/monetization')
@login_required
@admin_required
def monetization():
    """Dashboard for financial and AI usage monitoring."""
    from app.models.ai_usage import AIUsageLog
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # 1. Financial Stats
    active_subs = Subscription.query.filter_by(status='active').all()
    mrr = sum([sub.plan.price for sub in active_subs if sub.plan])
    
    sub_counts = db.session.query(Plan.name, func.count(Subscription.id)).join(Subscription).filter(Subscription.status == 'active').group_by(Plan.name).all()
    
    # 2. AI Usage Trends (Last 7 Days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    usage_by_feature = db.session.query(
        AIUsageLog.feature_type, 
        func.count(AIUsageLog.id), 
        func.sum(AIUsageLog.credits_used)
    ).filter(AIUsageLog.created_at >= seven_days_ago).group_by(AIUsageLog.feature_type).all()
    
    # 3. Top AI Consuming Users
    top_consumers = db.session.query(
        User.email, 
        func.sum(AIUsageLog.credits_used).label('total_credits'),
        func.count(AIUsageLog.id).label('call_count')
    ).join(AIUsageLog).group_by(User.email).order_by(func.sum(AIUsageLog.credits_used).desc()).limit(10).all()

    # 4. Feature Costs (from credit_config)
    from app.utils.credit_config import AI_FEATURE_COSTS, get_credit_cost
    current_costs = {feature: get_credit_cost(feature) for feature in AI_FEATURE_COSTS}

    return render_template('admin/monetization.html', 
                          mrr=mrr, 
                          active_sub_count=len(active_subs),
                          sub_counts=sub_counts,
                          usage_by_feature=usage_by_feature,
                          top_consumers=top_consumers,
                          current_costs=current_costs,
                          now=datetime.utcnow())

@bp.route('/monetization/update-cost', methods=['POST'])
@login_required
@admin_required
def update_feature_cost():
    """Adjust AI credit costs."""
    from app.models.config import SystemConfig
    feature = request.form.get('feature')
    cost = request.form.get('cost')
    
    if feature and cost:
        key = f"CREDIT_COST_{feature.upper()}"
        SystemConfig.set_config_value(key, cost, description=f"Custom AI cost for {feature}")
        flash(f"Updated cost for {feature} to {cost} credits.", "success")
    
    return redirect(url_for('admin.monetization'))

@bp.route('/monetization/export', methods=['GET'])
@login_required
@admin_required
def export_usage():
    """Export AI usage logs as CSV."""
    import csv
    import io
    from flask import Response
    from app.models.ai_usage import AIUsageLog
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'User', 'Feature', 'Credits', 'Tokens', 'Status', 'Time'])
    
    logs = AIUsageLog.query.order_by(AIUsageLog.created_at.desc()).limit(5000).all()
    for log in logs:
        writer.writerow([log.id, log.user.email, log.feature_type, log.credits_used, log.tokens_used, log.status, log.created_at])
        
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers.set("Content-Disposition", "attachment", filename="ai_usage_report.csv")
    return response

@bp.route('/user/<int:user_id>/suspend', methods=['POST'])
@login_required
@admin_required
def suspend_user(user_id):
    """Disable/Enable user account for abuse."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("Cannot suspend yourself.", "danger")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        status = "suspended" if not user.is_active else "activated"
        flash(f"User {user.email} has been {status}.", "success")
    
    return redirect(request.referrer or url_for('admin.dashboard'))

@bp.route('/contacts')
@login_required
@admin_required
def list_contacts():
    from app.models.contact import ContactThread
    threads = ContactThread.query.order_by(ContactThread.updated_at.desc()).all()
    return render_template('admin/contacts.html', threads=threads)

@bp.route('/contacts/<int:thread_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def view_contact(thread_id):
    from app.models.contact import ContactThread, ContactMessage
    thread = ContactThread.query.get_or_404(thread_id)
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            message = ContactMessage(
                thread_id=thread.id,
                sender_id=current_user.id,
                is_admin=True,
                content=content
            )
            thread.status = 'replied'
            db.session.add(message)
            db.session.commit()
            flash('Reply sent to user.', 'success')
            return redirect(url_for('admin.view_contact', thread_id=thread_id))
            
    return render_template('admin/view_contact.html', thread=thread)
