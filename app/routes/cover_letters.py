"""
Cover Letter Routes

Handles cover letter generation, templates, and management.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import CoverLetter, UserProfile, JobPost
from app.services.cover_letter_generator import CoverLetterGenerator, generate_cover_letter
from app import db
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('cover_letters', __name__, url_prefix='/cover-letters')


@bp.route('/', methods=['GET'])
@login_required
def index():
    """List all cover letters"""
    cover_letters = CoverLetter.query.filter_by(user_id=current_user.id).order_by(CoverLetter.created_at.desc()).all()
    return render_template('cover_letters/index.html', cover_letters=cover_letters)


@bp.route('/generate', methods=['GET', 'POST'])
@login_required
async def generate():
    """Generate a new cover letter"""
    
    if request.method == 'POST':
        try:
            # Get form data
            job_title = request.form.get('job_title')
            company_name = request.form.get('company_name')
            job_description = request.form.get('job_description', '')
            tone = request.form.get('tone', 'professional')
            job_id = request.form.get('job_id')  # Optional: link to a job
            
            if not job_title or not company_name:
                flash('Job title and company name are required', 'danger')
                return redirect(url_for('cover_letters.generate'))
            
            # Get user profile
            user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
            
            # Build profile dict
            profile_data = {
                'skills': user_profile.skills if user_profile else 'Not specified',
                'experience': user_profile.experience if user_profile else 'Not specified',
                'preferred_roles': user_profile.preferred_roles if user_profile else 'Not specified'
            }
            
            # Generate cover letter (Metered)
            generator = CoverLetterGenerator()
            content = await generator.generate(
                user_id=current_user.id,
                job_title=job_title,
                company_name=company_name,
                job_description=job_description,
                user_profile=profile_data,
                tone=tone
            )
            
            # Save to database
            cover_letter = CoverLetter(
                user_id=current_user.id,
                content=content
            )
            db.session.add(cover_letter)
            db.session.commit()
            
            flash('Cover letter generated successfully!', 'success')
            return redirect(url_for('cover_letters.view', id=cover_letter.id))
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {str(e)}")
            flash(f'Error generating cover letter: {str(e)}', 'danger')
            return redirect(url_for('cover_letters.generate'))
    
    # GET request - show form
    # Get recent jobs for quick selection
    recent_jobs = JobPost.query.order_by(JobPost.ingested_at.desc()).limit(10).all()
    
    return render_template('cover_letters/generate.html', recent_jobs=recent_jobs)


@bp.route('/templates', methods=['GET'])
@login_required
def templates():
    """View available templates"""
    generator = CoverLetterGenerator()
    available_templates = generator.get_templates()
    return render_template('cover_letters/templates.html', templates=available_templates)


@bp.route('/from-template/<template_name>', methods=['GET', 'POST'])
@login_required
def from_template(template_name):
    """Create cover letter from template"""
    
    generator = CoverLetterGenerator()
    available_templates = generator.get_templates()
    
    if template_name not in available_templates:
        flash('Template not found', 'danger')
        return redirect(url_for('cover_letters.templates'))
    
    template = available_templates[template_name]
    
    if request.method == 'POST':
        try:
            # Get customization data
            replacements = {
                'Job Title': request.form.get('job_title', ''),
                'Company Name': request.form.get('company_name', ''),
                'Years': request.form.get('years', ''),
                'Field': request.form.get('field', ''),
                'Skills': request.form.get('skills', ''),
                'Your Name': request.form.get('your_name', ''),
                'Your Contact': request.form.get('your_contact', ''),
                'Previous Company': request.form.get('previous_company', ''),
                'Achievement': request.form.get('achievement', ''),
                'Impact': request.form.get('impact', ''),
                'Reason': request.form.get('reason', ''),
                'Key Skills': request.form.get('key_skills', ''),
                'Industry': request.form.get('industry', ''),
                'Area of Interest': request.form.get('area_of_interest', ''),
                'Project/Initiative': request.form.get('project', ''),
                'Goal': request.form.get('goal', ''),
                'Key Competency': request.form.get('competency', ''),
                'Previous Field': request.form.get('previous_field', ''),
                'New Field': request.form.get('new_field', ''),
                'Transferable Skills': request.form.get('transferable_skills', ''),
                'Relevant Experience': request.form.get('relevant_experience', ''),
                'Learning/Preparation Activities': request.form.get('preparation', '')
            }
            
            # Customize template
            content = generator.customize_template(template['content'], replacements)
            
            # Save to database
            cover_letter = CoverLetter(
                user_id=current_user.id,
                content=content
            )
            db.session.add(cover_letter)
            db.session.commit()
            
            flash('Cover letter created from template!', 'success')
            return redirect(url_for('cover_letters.view', id=cover_letter.id))
            
        except Exception as e:
            logger.error(f"Error creating from template: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('cover_letters.from_template', template_name=template_name))
    
    # Get user profile for auto-filling
    user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    
    return render_template('cover_letters/from_template.html', 
                         template=template, 
                         template_name=template_name,
                         user_profile=user_profile,
                         current_user=current_user)


@bp.route('/view/<int:id>', methods=['GET'])
@login_required
def view(id):
    """View a specific cover letter"""
    cover_letter = CoverLetter.query.get_or_404(id)
    
    # Check ownership
    if cover_letter.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('cover_letters.index'))
    
    return render_template('cover_letters/view.html', cover_letter=cover_letter)


@bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit a cover letter"""
    cover_letter = CoverLetter.query.get_or_404(id)
    
    # Check ownership
    if cover_letter.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('cover_letters.index'))
    
    if request.method == 'POST':
        try:
            content = request.form.get('content')
            
            if not content:
                flash('Content cannot be empty', 'danger')
                return redirect(url_for('cover_letters.edit', id=id))
            
            cover_letter.content = content
            db.session.commit()
            
            flash('Cover letter updated successfully!', 'success')
            return redirect(url_for('cover_letters.view', id=id))
            
        except Exception as e:
            logger.error(f"Error updating cover letter: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('cover_letters.edit', id=id))
    
    return render_template('cover_letters/edit.html', cover_letter=cover_letter)


@bp.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    """Delete a cover letter"""
    cover_letter = CoverLetter.query.get_or_404(id)
    
    # Check ownership
    if cover_letter.user_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('cover_letters.index'))
    
    try:
        db.session.delete(cover_letter)
        db.session.commit()
        flash('Cover letter deleted', 'success')
    except Exception as e:
        logger.error(f"Error deleting cover letter: {str(e)}")
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('cover_letters.index'))


@bp.route('/api/generate', methods=['POST'])
@login_required
async def api_generate():
    """API endpoint for generating cover letters"""
    try:
        data = request.get_json()
        
        job_title = data.get('job_title')
        company_name = data.get('company_name')
        job_description = data.get('job_description', '')
        tone = data.get('tone', 'professional')
        
        if not job_title or not company_name:
            return jsonify({
                'success': False,
                'message': 'Job title and company name are required'
            }), 400
        
        # Get user profile
        user_profile = UserProfile.query.filter_by(user_id=current_user.id).first()
        
        profile_data = {
            'skills': user_profile.skills if user_profile else 'Not specified',
            'experience': user_profile.experience if user_profile else 'Not specified',
            'preferred_roles': user_profile.preferred_roles if user_profile else 'Not specified'
        }
        
        # Generate (Metered)
        content = await generate_cover_letter(
            user_id=current_user.id,
            job_title=job_title,
            company_name=company_name,
            job_description=job_description,
            user_profile=profile_data,
            tone=tone
        )
        
        return jsonify({
            'success': True,
            'content': content
        })
        
    except Exception as e:
        logger.error(f"API generate error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
