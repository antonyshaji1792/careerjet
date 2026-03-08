"""
API Endpoints for Skill Gap Analysis Integration
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Resume, JobPost
from app.models.skill_intelligence import (
    ResumeSkillExtracted,
    JobSkillExtracted,
    SkillGapAnalysis
)
from app.services.skill_extraction_service import SkillExtractionService
from app.services.enhanced_skill_gap_service import EnhancedSkillGapService
from app.services.skill_recommendation_service import SkillRecommendationService
from app.services.ats_impact_simulator import ATSImpactSimulator
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('skill_gap_ui', __name__, url_prefix='/api/skill-gap-ui')


@bp.route('/analyze/<int:resume_id>', methods=['POST'])
@login_required
def analyze_resume_gaps(resume_id):
    """
    Analyze skill gaps for a resume against a job description.
    Used by Resume Builder UI.
    """
    try:
        # Get resume
        resume = Resume.query.filter_by(
            id=resume_id,
            user_id=current_user.id
        ).first()
        
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Get job description from request
        data = request.get_json()
        job_description = data.get('job_description', '')
        job_id = data.get('job_id')
        
        if not job_description and not job_id:
            return jsonify({'error': 'Job description or job ID required'}), 400
        
        # Extract skills from resume if not already done
        extraction_service = SkillExtractionService()
        resume_text = resume.content_json.get('full_text', '')
        
        if not resume_text:
            return jsonify({'error': 'Resume has no content'}), 400
        
        # Extract resume skills
        resume_skills_data = extraction_service.extract_from_resume(resume_text)
        
        # Save to database
        _save_resume_skills(resume.id, current_user.id, resume_skills_data)
        
        # Extract job skills
        if job_id:
            job = JobPost.query.get(job_id)
            if job:
                job_description = job.description
        
        job_skills_data = extraction_service.extract_from_job_description(job_description)
        
        # Create temporary job if needed
        if not job_id:
            job = JobPost(
                title='Target Role',
                company='Target Company',
                description=job_description,
                location='Remote'
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id
        
        # Save job skills
        _save_job_skills(job_id, job_skills_data)
        
        # Perform gap analysis
        gap_service = EnhancedSkillGapService()
        analysis = gap_service.analyze_gap(
            resume_id=resume.id,
            job_id=job_id,
            user_id=current_user.id,
            save_to_db=True
        )
        
        # Get recommendations
        recommendation_service = SkillRecommendationService()
        missing_skills = (
            analysis['gaps']['missing_mandatory'] +
            analysis['gaps']['missing_preferred']
        )
        
        recommendations = recommendation_service.get_bulk_recommendations(missing_skills)
        
        # Get ATS predictions
        simulator = ATSImpactSimulator()
        
        # Convert to simulator format
        current_resume_skills = [
            {
                'skill_name_normalized': s.skill_name_normalized,
                'skill_name': s.skill_name,
                'proficiency_level': s.proficiency_level,
                'years_of_experience': s.years_of_experience,
                'category': s.category
            }
            for s in ResumeSkillExtracted.query.filter_by(resume_id=resume.id).all()
        ]
        
        job_skills = [
            {
                'skill_name_normalized': s.skill_name_normalized,
                'skill_name': s.skill_name,
                'requirement_type': s.requirement_type,
                'category': s.category
            }
            for s in JobSkillExtracted.query.filter_by(job_id=job_id).all()
        ]
        
        # Get top 3 skills to add
        top_skills = simulator.get_top_skills_to_add(
            current_resume_skills,
            job_skills,
            missing_skills[:10],  # Top 10 missing
            count=3
        )
        
        # Build response
        return jsonify({
            'success': True,
            'analysis': {
                'summary': analysis['summary'],
                'gaps': analysis['gaps'],
                'matched_skills': analysis['matched_skills'],
                'ats_impact': analysis['ats_impact'],
                'hiring_relevance': analysis['hiring_relevance']
            },
            'recommendations': recommendations[:10],  # Top 10
            'top_skills_to_add': top_skills,
            'resume_id': resume.id,
            'job_id': job_id
        })
        
    except Exception as e:
        logger.error(f"Gap analysis failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/predict-impact/<int:resume_id>', methods=['POST'])
@login_required
def predict_skill_impact(resume_id):
    """
    Predict ATS score impact of adding a skill.
    """
    try:
        # Get resume
        resume = Resume.query.filter_by(
            id=resume_id,
            user_id=current_user.id
        ).first()
        
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Get skill to add
        data = request.get_json()
        skill_to_add = data.get('skill')
        job_id = data.get('job_id')
        
        if not skill_to_add or not job_id:
            return jsonify({'error': 'Skill and job_id required'}), 400
        
        # Get current skills
        current_skills = [
            {
                'skill_name_normalized': s.skill_name_normalized,
                'skill_name': s.skill_name,
                'proficiency_level': s.proficiency_level,
                'years_of_experience': s.years_of_experience,
                'category': s.category
            }
            for s in ResumeSkillExtracted.query.filter_by(resume_id=resume.id).all()
        ]
        
        # Get job skills
        job_skills = [
            {
                'skill_name_normalized': s.skill_name_normalized,
                'skill_name': s.skill_name,
                'requirement_type': s.requirement_type,
                'category': s.category
            }
            for s in JobSkillExtracted.query.filter_by(job_id=job_id).all()
        ]
        
        # Predict impact
        simulator = ATSImpactSimulator()
        prediction = simulator.predict_score_change(
            current_skills,
            job_skills,
            skill_to_add
        )
        
        return jsonify({
            'success': True,
            'prediction': prediction
        })
        
    except Exception as e:
        logger.error(f"Impact prediction failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@bp.route('/add-skill-to-resume/<int:resume_id>', methods=['POST'])
@login_required
def add_skill_to_resume(resume_id):
    """
    Add a skill to resume (non-destructive).
    """
    try:
        # Get resume
        resume = Resume.query.filter_by(
            id=resume_id,
            user_id=current_user.id
        ).first()
        
        if not resume:
            return jsonify({'error': 'Resume not found'}), 404
        
        # Get skill data
        data = request.get_json()
        skill_name = data.get('skill_name')
        skill_key = data.get('skill_key')
        proficiency = data.get('proficiency', 'intermediate')
        
        if not skill_name or not skill_key:
            return jsonify({'error': 'Skill name and key required'}), 400
        
        # Add to resume skills (database)
        existing = ResumeSkillExtracted.query.filter_by(
            resume_id=resume.id,
            skill_name_normalized=skill_key
        ).first()
        
        if existing:
            return jsonify({'error': 'Skill already in resume'}), 400
        
        # Create new skill entry
        new_skill = ResumeSkillExtracted(
            resume_id=resume.id,
            user_id=current_user.id,
            skill_name=skill_name,
            skill_name_normalized=skill_key,
            category=data.get('category', 'hard_skill'),
            proficiency_level=proficiency,
            source='user_added',
            confidence_score=1.0
        )
        
        db.session.add(new_skill)
        
        # Update resume content_json (non-destructive)
        content = resume.content_json or {}
        skills_section = content.get('skills', [])
        
        if skill_name not in skills_section:
            skills_section.append(skill_name)
            content['skills'] = skills_section
            resume.content_json = content
        
        db.session.commit()
        
        # Get recommendation for this skill
        recommendation_service = SkillRecommendationService()
        recommendation = recommendation_service.get_recommendations_for_skill(
            skill_name=skill_name,
            skill_key=skill_key,
            gap_type='missing'
        )
        
        return jsonify({
            'success': True,
            'message': f'Added {skill_name} to resume',
            'skill': {
                'name': skill_name,
                'key': skill_key,
                'proficiency': proficiency
            },
            'recommendation': recommendation
        })
        
    except Exception as e:
        logger.error(f"Add skill failed: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


def _save_resume_skills(resume_id: int, user_id: int, skills_data: list):
    """Helper to save resume skills"""
    # Delete existing
    ResumeSkillExtracted.query.filter_by(resume_id=resume_id).delete()
    
    # Add new
    for skill_data in skills_data:
        skill = ResumeSkillExtracted(
            resume_id=resume_id,
            user_id=user_id,
            **skill_data
        )
        db.session.add(skill)
    
    db.session.commit()


def _save_job_skills(job_id: int, skills_data: list):
    """Helper to save job skills"""
    # Delete existing
    JobSkillExtracted.query.filter_by(job_id=job_id).delete()
    
    # Add new
    for skill_data in skills_data:
        skill = JobSkillExtracted(
            job_id=job_id,
            **skill_data
        )
        db.session.add(skill)
    
    db.session.commit()
