"""
Skill Gap Analysis API Endpoints
Integrates with Resume Builder, ATS Engine, Job Matching, and Auto-Apply
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import logging

from app.services.skill_gap_service import SkillGapService
from app.services.ats_scoring_service import ATSScoringService
from app.models import Resume, JobPost, UserProfile, db
from app.utils.credit_middleware import credit_required

logger = logging.getLogger(__name__)

# Create blueprint
skill_gap_bp = Blueprint('skill_gap', __name__, url_prefix='/api/skill-gap')


# Rate limiting decorator
def rate_limit(max_per_minute=10):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # TODO: Implement proper rate limiting with Redis
            return f(*args, **kwargs)
        return wrapped
    return decorator


@skill_gap_bp.route('/analyze', methods=['POST'])
@login_required
@credit_required('skill_gap_analysis')
@rate_limit(max_per_minute=10)
def analyze_skill_gap():

    """
    Analyze skill gap between resume and job description.
    
    Request:
    {
        "resume_id": 123,
        "job_description": "...",
        "job_id": 456  // optional
    }
    
    Response:
    {
        "success": true,
        "analysis": {...},
        "ats_integration": {...},
        "market_insights": {...}
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        resume_id = data.get('resume_id')
        job_description = data.get('job_description')
        job_id = data.get('job_id')
        
        if not resume_id or not job_description:
            return jsonify({
                'success': False,
                'message': 'resume_id and job_description are required'
            }), 400
        
        # Get resume
        resume = Resume.query.filter_by(
            id=resume_id,
            user_id=current_user.id
        ).first()
        
        if not resume:
            return jsonify({
                'success': False,
                'message': 'Resume not found'
            }), 404
        
        # Extract resume skills
        resume_data = resume.content_json or {}
        resume_skills = resume_data.get('skills', [])
        resume_text = str(resume_data)
        
        # Perform skill gap analysis
        service = SkillGapService()
        analysis = service.analyze_skill_gap(
            resume_skills=resume_skills,
            job_description=job_description,
            resume_text=resume_text
        )
        
        # Integrate with ATS scoring
        ats_service = ATSScoringService()
        ats_report = ats_service.calculate_ats_score(
            resume_data=resume_data,
            job_description=job_description
        )
        
        # Get market insights if job_id provided
        market_insights = None
        if job_id:
            market_insights = _get_market_insights(job_id)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'ats_integration': {
                'current_score': ats_report['overall_score'],
                'grade': ats_report['grade'],
                'potential_score': analysis['summary']['potential_score'],
                'improvement_potential': round(
                    analysis['summary']['potential_score'] - ats_report['overall_score'],
                    1
                )
            },
            'market_insights': market_insights
        }), 200
        
    except Exception as e:
        logger.error(f"Skill gap analysis failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Analysis failed: {str(e)}'
        }), 500


@skill_gap_bp.route('/compare-market', methods=['POST'])
@login_required
@rate_limit(max_per_minute=5)
def compare_with_market():
    """
    Compare resume skills with market expectations.
    
    Request:
    {
        "resume_id": 123,
        "role": "Software Engineer",
        "location": "Remote"
    }
    
    Response:
    {
        "success": true,
        "market_analysis": {...}
    }
    """
    try:
        data = request.get_json()
        
        resume_id = data.get('resume_id')
        role = data.get('role')
        location = data.get('location', 'Remote')
        
        if not resume_id or not role:
            return jsonify({
                'success': False,
                'message': 'resume_id and role are required'
            }), 400
        
        # Get resume
        resume = Resume.query.filter_by(
            id=resume_id,
            user_id=current_user.id
        ).first()
        
        if not resume:
            return jsonify({
                'success': False,
                'message': 'Resume not found'
            }), 404
        
        # Get market data from job posts
        market_data = _analyze_market_expectations(role, location)
        
        # Extract resume skills
        resume_data = resume.content_json or {}
        resume_skills = resume_data.get('skills', [])
        
        # Compare with market
        service = SkillGapService()
        
        # Aggregate job descriptions
        aggregated_jd = _aggregate_job_descriptions(market_data['jobs'])
        
        # Perform analysis
        analysis = service.analyze_skill_gap(
            resume_skills=resume_skills,
            job_description=aggregated_jd
        )
        
        return jsonify({
            'success': True,
            'market_analysis': {
                'role': role,
                'location': location,
                'jobs_analyzed': len(market_data['jobs']),
                'top_skills': market_data['top_skills'],
                'skill_frequency': market_data['skill_frequency'],
                'your_coverage': analysis['summary']['match_percentage'],
                'gaps': analysis['skill_gaps'],
                'recommendations': analysis['recommendations']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Market comparison failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Market comparison failed: {str(e)}'
        }), 500


@skill_gap_bp.route('/learning-path/<int:resume_id>', methods=['POST'])
@login_required
@rate_limit(max_per_minute=10)
def get_learning_path(resume_id):
    """
    Get personalized learning path.
    
    Request:
    {
        "job_description": "...",
        "focus_skills": ["python", "aws"]  // optional
    }
    
    Response:
    {
        "success": true,
        "learning_path": {...}
    }
    """
    try:
        data = request.get_json()
        job_description = data.get('job_description')
        focus_skills = data.get('focus_skills', [])
        
        if not job_description:
            return jsonify({
                'success': False,
                'message': 'job_description is required'
            }), 400
        
        # Get resume
        resume = Resume.query.filter_by(
            id=resume_id,
            user_id=current_user.id
        ).first()
        
        if not resume:
            return jsonify({
                'success': False,
                'message': 'Resume not found'
            }), 404
        
        # Extract skills
        resume_data = resume.content_json or {}
        resume_skills = resume_data.get('skills', [])
        
        # Analyze
        service = SkillGapService()
        analysis = service.analyze_skill_gap(
            resume_skills=resume_skills,
            job_description=job_description
        )
        
        # Filter by focus skills if provided
        learning_paths = analysis['learning_paths']
        if focus_skills:
            learning_paths = [
                lp for lp in learning_paths
                if lp['skill'].lower() in [s.lower() for s in focus_skills]
            ]
        
        return jsonify({
            'success': True,
            'learning_path': {
                'total_skills': len(learning_paths),
                'estimated_time': _calculate_total_time(learning_paths),
                'paths': learning_paths,
                'score_predictions': analysis['score_predictions']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Learning path generation failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Learning path generation failed: {str(e)}'
        }), 500


@skill_gap_bp.route('/auto-apply-readiness/<int:resume_id>/<int:job_id>', methods=['GET'])
@login_required
@rate_limit(max_per_minute=20)
def check_auto_apply_readiness(resume_id, job_id):
    """
    Check if resume is ready for auto-apply to a job.
    
    Response:
    {
        "success": true,
        "ready": true/false,
        "match_score": 85.5,
        "missing_critical_skills": [...],
        "recommendation": "..."
    }
    """
    try:
        # Get resume
        resume = Resume.query.filter_by(
            id=resume_id,
            user_id=current_user.id
        ).first()
        
        if not resume:
            return jsonify({
                'success': False,
                'message': 'Resume not found'
            }), 404
        
        # Get job
        job = JobPost.query.get(job_id)
        if not job:
            return jsonify({
                'success': False,
                'message': 'Job not found'
            }), 404
        
        # Extract data
        resume_data = resume.content_json or {}
        resume_skills = resume_data.get('skills', [])
        job_description = job.description or ''
        
        # Analyze
        service = SkillGapService()
        analysis = service.analyze_skill_gap(
            resume_skills=resume_skills,
            job_description=job_description
        )
        
        # Determine readiness
        match_score = analysis['summary']['match_percentage']
        mandatory_missing = analysis['summary']['mandatory_missing']
        
        # Readiness criteria
        ready = match_score >= 60 and mandatory_missing == 0
        
        if ready:
            recommendation = "Resume is ready for auto-apply!"
        elif mandatory_missing > 0:
            recommendation = f"Add {mandatory_missing} mandatory skills before applying"
        else:
            recommendation = f"Improve match score to at least 60% (currently {match_score}%)"
        
        return jsonify({
            'success': True,
            'ready': ready,
            'match_score': match_score,
            'missing_critical_skills': analysis['skill_gaps']['mandatory'],
            'missing_preferred_skills': analysis['skill_gaps']['preferred'],
            'recommendation': recommendation,
            'top_gaps': analysis['ranked_gaps'][:5]
        }), 200
        
    except Exception as e:
        logger.error(f"Auto-apply readiness check failed: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Readiness check failed: {str(e)}'
        }), 500


# ============================================================================
# Helper Functions
# ============================================================================

def _get_market_insights(job_id: int) -> dict:
    """Get market insights for a specific job"""
    try:
        job = JobPost.query.get(job_id)
        if not job:
            return None
        
        # Find similar jobs
        similar_jobs = JobPost.query.filter(
            JobPost.title.ilike(f'%{job.title}%')
        ).limit(20).all()
        
        # Extract common skills
        all_skills = []
        for j in similar_jobs:
            if j.description:
                service = SkillGapService()
                skills = service._extract_skills_from_text(j.description.lower())
                all_skills.extend(skills)
        
        # Count frequency
        from collections import Counter
        skill_freq = Counter(all_skills)
        
        return {
            'similar_jobs_count': len(similar_jobs),
            'top_skills': [skill for skill, _ in skill_freq.most_common(10)],
            'skill_frequency': dict(skill_freq.most_common(20))
        }
        
    except Exception as e:
        logger.error(f"Market insights failed: {str(e)}")
        return None


def _analyze_market_expectations(role: str, location: str) -> dict:
    """Analyze market expectations for a role"""
    try:
        # Query recent jobs
        jobs = JobPost.query.filter(
            JobPost.title.ilike(f'%{role}%')
        ).limit(50).all()
        
        # Extract skills from all jobs
        all_skills = []
        service = SkillGapService()
        
        for job in jobs:
            if job.description:
                skills = service._extract_skills_from_text(job.description.lower())
                all_skills.extend(skills)
        
        # Count frequency
        from collections import Counter
        skill_freq = Counter(all_skills)
        
        return {
            'jobs': jobs,
            'top_skills': [skill for skill, _ in skill_freq.most_common(15)],
            'skill_frequency': dict(skill_freq.most_common(30))
        }
        
    except Exception as e:
        logger.error(f"Market analysis failed: {str(e)}")
        return {'jobs': [], 'top_skills': [], 'skill_frequency': {}}


def _aggregate_job_descriptions(jobs: list) -> str:
    """Aggregate multiple job descriptions"""
    descriptions = []
    for job in jobs[:20]:  # Limit to 20 jobs
        if job.description:
            descriptions.append(job.description)
    
    return '\n\n'.join(descriptions)


def _calculate_total_time(learning_paths: list) -> str:
    """Calculate total estimated learning time"""
    # Simple aggregation
    if not learning_paths:
        return "0 weeks"
    
    # Rough estimate based on number of skills
    weeks = len(learning_paths) * 2  # 2 weeks per skill on average
    
    if weeks < 4:
        return f"{weeks} weeks"
    else:
        months = weeks // 4
        return f"{months} months"


# Error handlers
@skill_gap_bp.errorhandler(400)
def bad_request(e):
    return jsonify({'success': False, 'message': 'Bad request'}), 400


@skill_gap_bp.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'message': 'Resource not found'}), 404


@skill_gap_bp.errorhandler(500)
def internal_error(e):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500
