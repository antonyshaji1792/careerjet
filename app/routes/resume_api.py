"""
Resume Builder REST API Routes
Secure, auth-protected endpoints with role-based access control
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
import json
import logging

from app.extensions import db
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.models.resume_sections import (
    ResumeSection, ResumeSummary, ResumeExperience,
    ResumeEducation, ResumeProject, ResumeCertification
)
from app.models.resume_metrics import ResumeActivityLog
from app.services.security_guard import (
    SecurityGuard, require_resume_access, rate_limit_route, sanitize_input
)

logger = logging.getLogger(__name__)

# Create blueprint
resume_api = Blueprint('resume_api', __name__, url_prefix='/api/resumes')


# ============================================================================
# Decorators
# ============================================================================

def validate_json(required_fields=None):
    """Validate JSON request body"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Content-Type must be application/json',
                    'error_code': 'INVALID_CONTENT_TYPE'
                }), 400
            
            data = request.get_json()
            
            if required_fields:
                missing = [field for field in required_fields if field not in data]
                if missing:
                    return jsonify({
                        'success': False,
                        'message': f'Missing required fields: {", ".join(missing)}',
                        'error_code': 'MISSING_FIELDS'
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_optimistic_lock(f):
    """Check version for optimistic locking"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        resume_id = kwargs.get('resume_id')
        data = request.get_json()
        
        if 'version' in data:
            resume = Resume.query.get(resume_id)
            if resume and resume.updated_at:
                client_version = datetime.fromisoformat(data['version'])
                if resume.updated_at > client_version:
                    return jsonify({
                        'success': False,
                        'message': 'Resume has been modified by another user. Please refresh.',
                        'error_code': 'OPTIMISTIC_LOCK_FAILURE',
                        'server_version': resume.updated_at.isoformat()
                    }), 409
        
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# Resume CRUD Operations
# ============================================================================

@resume_api.route('', methods=['POST'])
@login_required
@rate_limit_route(max_requests=10, time_window=3600)  # 10 per hour
@validate_json(required_fields=['title'])
@sanitize_input
def create_resume():
    """
    Create a new resume
    
    POST /api/resumes
    {
        "title": "My Resume",
        "template_id": "modern_tech",
        "is_primary": false
    }
    """
    try:
        data = request.get_json()
        
        # Sanitize inputs
        title = SecurityGuard.sanitize_html(data.get('title', 'My Resume'))
        template_id = data.get('template_id', 'modern_tech')
        is_primary = data.get('is_primary', False)
        
        # If setting as primary, unset other primary resumes
        if is_primary:
            Resume.query.filter_by(
                user_id=current_user.id,
                is_primary=True
            ).update({'is_primary': False})
        
        # Create resume
        resume = Resume(
            user_id=current_user.id,
            title=title,
            template_id=template_id,
            is_primary=is_primary,
            is_generated=False,
            is_active=True
        )
        
        db.session.add(resume)
        db.session.commit()
        
        # Log activity
        ResumeActivityLog.log_activity(
            resume_id=resume.id,
            action='created',
            user_id=current_user.id,
            details={'title': title, 'template': template_id},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        logger.info(f"Resume created: {resume.id} by user {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Resume created successfully',
            'resume': {
                'id': resume.id,
                'title': resume.title,
                'template_id': resume.template_id,
                'is_primary': resume.is_primary,
                'created_at': resume.created_at.isoformat(),
                'updated_at': resume.updated_at.isoformat() if resume.updated_at else None
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating resume: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to create resume',
            'error_code': 'CREATE_FAILED'
        }), 500


@resume_api.route('/<int:resume_id>/clone', methods=['POST'])
@login_required
@require_resume_access
@rate_limit_route(max_requests=5, time_window=3600)  # 5 per hour
@validate_json()
def clone_resume(resume_id):
    """
    Clone an existing resume
    
    POST /api/resumes/{id}/clone
    {
        "title": "Cloned Resume",
        "clone_sections": true
    }
    """
    try:
        original = Resume.query.get_or_404(resume_id)
        data = request.get_json() or {}
        
        # Create clone
        title = SecurityGuard.sanitize_html(
            data.get('title', f"{original.title} (Copy)")
        )
        
        cloned = Resume(
            user_id=current_user.id,
            title=title,
            template_id=original.template_id,
            content_json=original.content_json,
            is_primary=False,
            is_generated=original.is_generated,
            is_active=True
        )
        
        db.session.add(cloned)
        db.session.flush()
        
        # Clone sections if requested
        if data.get('clone_sections', True):
            # Clone experiences
            for exp in ResumeExperience.query.filter_by(
                resume_id=resume_id,
                is_active=True
            ).all():
                cloned_exp = ResumeExperience(
                    resume_id=cloned.id,
                    company_name=exp.company_name,
                    job_title=exp.job_title,
                    location=exp.location,
                    start_date=exp.start_date,
                    end_date=exp.end_date,
                    is_current=exp.is_current,
                    description=exp.description,
                    achievements=exp.achievements,
                    display_order=exp.display_order
                )
                db.session.add(cloned_exp)
            
            # Clone education
            for edu in ResumeEducation.query.filter_by(
                resume_id=resume_id,
                is_active=True
            ).all():
                cloned_edu = ResumeEducation(
                    resume_id=cloned.id,
                    institution_name=edu.institution_name,
                    degree=edu.degree,
                    field_of_study=edu.field_of_study,
                    start_date=edu.start_date,
                    end_date=edu.end_date,
                    gpa=edu.gpa,
                    honors=edu.honors,
                    display_order=edu.display_order
                )
                db.session.add(cloned_edu)
            
            # Clone projects
            for proj in ResumeProject.query.filter_by(
                resume_id=resume_id,
                is_active=True
            ).all():
                cloned_proj = ResumeProject(
                    resume_id=cloned.id,
                    project_name=proj.project_name,
                    description=proj.description,
                    technologies=proj.technologies,
                    url=proj.url,
                    github_url=proj.github_url,
                    display_order=proj.display_order
                )
                db.session.add(cloned_proj)
        
        db.session.commit()
        
        # Log activity
        ResumeActivityLog.log_activity(
            resume_id=cloned.id,
            action='cloned',
            user_id=current_user.id,
            details={'original_id': resume_id, 'title': title},
            ip_address=request.remote_addr
        )
        
        logger.info(f"Resume cloned: {resume_id} -> {cloned.id}")
        
        return jsonify({
            'success': True,
            'message': 'Resume cloned successfully',
            'resume': {
                'id': cloned.id,
                'title': cloned.title,
                'original_id': resume_id,
                'created_at': cloned.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cloning resume: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to clone resume',
            'error_code': 'CLONE_FAILED'
        }), 500


@resume_api.route('/<int:resume_id>/sections/<section_type>', methods=['PUT'])
@login_required
@require_resume_access
@rate_limit_route(max_requests=50, time_window=3600)  # 50 per hour
@validate_json(required_fields=['content'])
@check_optimistic_lock
@sanitize_input
def update_resume_section(resume_id, section_type):
    """
    Update a specific resume section
    
    PUT /api/resumes/{id}/sections/{section_type}
    {
        "content": {...},
        "version": "2024-01-24T10:30:00"
    }
    """
    try:
        resume = Resume.query.get_or_404(resume_id)
        data = request.get_json()
        content = data['content']
        
        # Validate section type
        valid_sections = ['summary', 'experience', 'education', 'skills', 'projects', 'certifications']
        if section_type not in valid_sections:
            return jsonify({
                'success': False,
                'message': f'Invalid section type. Must be one of: {", ".join(valid_sections)}',
                'error_code': 'INVALID_SECTION_TYPE'
            }), 400
        
        # Handle different section types
        if section_type == 'experience':
            # Update or create experience
            exp_id = content.get('id')
            if exp_id:
                exp = ResumeExperience.query.filter_by(
                    id=exp_id,
                    resume_id=resume_id
                ).first_or_404()
            else:
                exp = ResumeExperience(resume_id=resume_id)
                db.session.add(exp)
            
            exp.company_name = SecurityGuard.sanitize_html(content.get('company_name', ''))
            exp.job_title = SecurityGuard.sanitize_html(content.get('job_title', ''))
            exp.location = content.get('location')
            exp.start_date = content.get('start_date')
            exp.end_date = content.get('end_date')
            exp.is_current = content.get('is_current', False)
            exp.description = SecurityGuard.sanitize_html(content.get('description', ''))
            exp.achievements = json.dumps(content.get('achievements', []))
            exp.display_order = content.get('display_order', 0)
            exp.updated_at = datetime.utcnow()
            
        elif section_type == 'education':
            edu_id = content.get('id')
            if edu_id:
                edu = ResumeEducation.query.filter_by(
                    id=edu_id,
                    resume_id=resume_id
                ).first_or_404()
            else:
                edu = ResumeEducation(resume_id=resume_id)
                db.session.add(edu)
            
            edu.institution_name = SecurityGuard.sanitize_html(content.get('institution_name', ''))
            edu.degree = SecurityGuard.sanitize_html(content.get('degree', ''))
            edu.field_of_study = content.get('field_of_study')
            edu.start_date = content.get('start_date')
            edu.end_date = content.get('end_date')
            edu.gpa = content.get('gpa')
            edu.honors = content.get('honors')
            edu.display_order = content.get('display_order', 0)
            edu.updated_at = datetime.utcnow()
        
        elif section_type == 'summary':
            summary_id = content.get('id')
            if summary_id:
                summary = ResumeSummary.query.filter_by(
                    id=summary_id,
                    resume_id=resume_id
                ).first_or_404()
            else:
                summary = ResumeSummary(resume_id=resume_id)
                db.session.add(summary)
            
            summary.summary_text = SecurityGuard.sanitize_html(content.get('summary_text', ''))
            summary.tone = content.get('tone', 'professional')
            summary.word_count = len(summary.summary_text.split())
            summary.updated_at = datetime.utcnow()
        
        # Update resume timestamp
        resume.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log activity
        ResumeActivityLog.log_activity(
            resume_id=resume_id,
            action='section_updated',
            user_id=current_user.id,
            details={'section_type': section_type},
            ip_address=request.remote_addr
        )
        
        logger.info(f"Resume section updated: {resume_id}/{section_type}")
        
        return jsonify({
            'success': True,
            'message': f'{section_type.capitalize()} section updated successfully',
            'updated_at': resume.updated_at.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating section: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to update section',
            'error_code': 'UPDATE_FAILED'
        }), 500


@resume_api.route('/<int:resume_id>/versions', methods=['POST'])
@login_required
@require_resume_access
@rate_limit_route(max_requests=20, time_window=3600)  # 20 per hour
@validate_json()
def create_resume_version(resume_id):
    """
    Create a new version of the resume
    
    POST /api/resumes/{id}/versions
    {
        "job_id": 100,
        "change_log": "Optimized for Software Engineer role"
    }
    """
    try:
        resume = Resume.query.get_or_404(resume_id)
        data = request.get_json() or {}
        
        # Get latest version number
        latest_version = ResumeVersion.query.filter_by(
            resume_id=resume_id
        ).order_by(ResumeVersion.version_number.desc()).first()
        
        version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Create new version
        version = ResumeVersion(
            resume_id=resume_id,
            job_id=data.get('job_id'),
            version_number=version_number,
            content_json=resume.content_json,
            ats_score=resume.ats_score,
            change_log=SecurityGuard.sanitize_html(
                data.get('change_log', f'Version {version_number}')
            )
        )
        
        db.session.add(version)
        db.session.commit()
        
        # Log activity
        ResumeActivityLog.log_activity(
            resume_id=resume_id,
            action='version_created',
            user_id=current_user.id,
            details={'version_number': version_number, 'job_id': data.get('job_id')},
            ip_address=request.remote_addr
        )
        
        logger.info(f"Resume version created: {resume_id} v{version_number}")
        
        return jsonify({
            'success': True,
            'message': 'Version created successfully',
            'version': {
                'id': version.id,
                'version_number': version.version_number,
                'job_id': version.job_id,
                'change_log': version.change_log,
                'created_at': version.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating version: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to create version',
            'error_code': 'VERSION_CREATE_FAILED'
        }), 500


@resume_api.route('/<int:resume_id>/versions/compare', methods=['POST'])
@login_required
@require_resume_access
@rate_limit_route(max_requests=30, time_window=3600)  # 30 per hour
@validate_json(required_fields=['version1_id', 'version2_id'])
def compare_resume_versions(resume_id):
    """
    Compare two resume versions
    
    POST /api/resumes/{id}/versions/compare
    {
        "version1_id": 1,
        "version2_id": 2
    }
    """
    try:
        data = request.get_json()
        
        version1 = ResumeVersion.query.filter_by(
            id=data['version1_id'],
            resume_id=resume_id
        ).first_or_404()
        
        version2 = ResumeVersion.query.filter_by(
            id=data['version2_id'],
            resume_id=resume_id
        ).first_or_404()
        
        # Get diff
        diff = version1.get_diff(version2)
        
        # Log activity
        ResumeActivityLog.log_activity(
            resume_id=resume_id,
            action='versions_compared',
            user_id=current_user.id,
            details={
                'version1': version1.version_number,
                'version2': version2.version_number
            },
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'success': True,
            'comparison': {
                'version1': {
                    'id': version1.id,
                    'number': version1.version_number,
                    'created_at': version1.created_at.isoformat(),
                    'change_log': version1.change_log
                },
                'version2': {
                    'id': version2.id,
                    'number': version2.version_number,
                    'created_at': version2.created_at.isoformat(),
                    'change_log': version2.change_log
                },
                'diff': diff
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error comparing versions: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to compare versions',
            'error_code': 'COMPARE_FAILED'
        }), 500


@resume_api.route('/<int:resume_id>/versions/<int:version_id>/rollback', methods=['POST'])
@login_required
@require_resume_access
@rate_limit_route(max_requests=10, time_window=3600)  # 10 per hour
def rollback_resume_version(resume_id, version_id):
    """
    Rollback resume to a previous version
    
    POST /api/resumes/{id}/versions/{version_id}/rollback
    """
    try:
        resume = Resume.query.get_or_404(resume_id)
        version = ResumeVersion.query.filter_by(
            id=version_id,
            resume_id=resume_id
        ).first_or_404()
        
        # Create backup of current state
        current_version = ResumeVersion(
            resume_id=resume_id,
            version_number=ResumeVersion.query.filter_by(
                resume_id=resume_id
            ).count() + 1,
            content_json=resume.content_json,
            ats_score=resume.ats_score,
            change_log=f'Backup before rollback to v{version.version_number}'
        )
        db.session.add(current_version)
        
        # Rollback to selected version
        resume.content_json = version.content_json
        resume.ats_score = version.ats_score
        resume.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log activity
        ResumeActivityLog.log_activity(
            resume_id=resume_id,
            action='rolled_back',
            user_id=current_user.id,
            details={
                'to_version': version.version_number,
                'backup_version': current_version.version_number
            },
            ip_address=request.remote_addr
        )
        
        logger.info(f"Resume rolled back: {resume_id} to v{version.version_number}")
        
        return jsonify({
            'success': True,
            'message': f'Resume rolled back to version {version.version_number}',
            'backup_version': current_version.version_number,
            'updated_at': resume.updated_at.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rolling back: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to rollback version',
            'error_code': 'ROLLBACK_FAILED'
        }), 500


@resume_api.route('/<int:resume_id>', methods=['DELETE'])
@login_required
@require_resume_access
@rate_limit_route(max_requests=10, time_window=3600)  # 10 per hour
def delete_resume(resume_id):
    """
    Soft delete a resume
    
    DELETE /api/resumes/{id}
    """
    try:
        resume = Resume.query.get_or_404(resume_id)
        
        # Soft delete
        resume.is_active = False
        resume.deleted_at = datetime.utcnow()
        
        # Soft delete all sections
        ResumeExperience.query.filter_by(resume_id=resume_id).update({
            'is_active': False,
            'deleted_at': datetime.utcnow()
        })
        
        ResumeEducation.query.filter_by(resume_id=resume_id).update({
            'is_active': False,
            'deleted_at': datetime.utcnow()
        })
        
        ResumeProject.query.filter_by(resume_id=resume_id).update({
            'is_active': False,
            'deleted_at': datetime.utcnow()
        })
        
        db.session.commit()
        
        # Log activity
        ResumeActivityLog.log_activity(
            resume_id=resume_id,
            action='deleted',
            user_id=current_user.id,
            details={'title': resume.title},
            ip_address=request.remote_addr
        )
        
        logger.info(f"Resume soft deleted: {resume_id}")
        
        return jsonify({
            'success': True,
            'message': 'Resume deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting resume: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to delete resume',
            'error_code': 'DELETE_FAILED'
        }), 500


# ============================================================================
# Error Handlers
# ============================================================================

@resume_api.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Resource not found',
        'error_code': 'NOT_FOUND'
    }), 404


@resume_api.errorhandler(403)
def forbidden(error):
    return jsonify({
        'success': False,
        'message': 'Permission denied',
        'error_code': 'PERMISSION_DENIED'
    }), 403


@resume_api.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({
        'success': False,
        'message': 'Rate limit exceeded. Please try again later.',
        'error_code': 'RATE_LIMIT_EXCEEDED'
    }), 429
