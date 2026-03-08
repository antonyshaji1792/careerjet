from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import JobPost, JobMatch

bp = Blueprint('jobs', __name__, url_prefix='/jobs')

@bp.route('/')
@login_required
def list_jobs():
    jobs = JobPost.query.all()
    return render_template('jobs/list.html', jobs=jobs)

@bp.route('/<int:job_id>')
@login_required
def detail(job_id):
    job = JobPost.query.get_or_404(job_id)
    return render_template('jobs/detail.html', job=job)
