from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import JobPost, JobMatch, Application

bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@bp.route('/')
@login_required
def index():
    from app.models import JobAlert
    
    # User-centric stats
    active_alerts = JobAlert.query.filter_by(user_id=current_user.id, is_active=True).count()
    matching_jobs = JobMatch.query.filter_by(user_id=current_user.id).count()
    applied_jobs = Application.query.filter_by(user_id=current_user.id, status='Applied').count()
    scheduled_jobs = Application.query.filter_by(user_id=current_user.id, status='Scheduled').count()
    
    recent_matches = JobMatch.query.filter_by(user_id=current_user.id).order_by(JobMatch.match_score.desc()).limit(10).all()
    
    return render_template('dashboard/index.html', 
                           active_alerts=active_alerts,
                           matching_jobs=matching_jobs,
                           applied_jobs=applied_jobs,
                           scheduled_jobs=scheduled_jobs,
                           recent_matches=recent_matches)
