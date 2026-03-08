from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import UserProfile, Resume, ResumeOptimization, db, PersonalDetails, Employment, KeySkill, ProfileSummary, CareerProfile
from app.services.resume_builder import ResumeBuilder
from app.services.experience_validator import ExperienceValidatorService
from app.services.bullet_scoring import BulletScoringService
from app.services.ats_simulator import ATSSimulatorService
from app.services.recruiter_scan import RecruiterScanService
from app.services.bias_detection import BiasDetectionService
from app.services.resume_integrity import ResumeIntegrityService
# Budget management removed in favor of credit system
from app.services.hybrid_enhancement import HybridEnhancementService
from app.services.decision_log import ResumeDecisionLogService
from app.utils.credit_middleware import credit_required
from app.utils.rate_limiter import rate_limit

import json
import logging
import tempfile
import os
from flask import send_file

logger = logging.getLogger(__name__)

bp = Blueprint('resumes', __name__, url_prefix='/resumes')

@bp.route('/builder', methods=['GET'])
@login_required
def builder_ui():
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    resumes = Resume.query.filter_by(user_id=current_user.id, is_active=True).order_by(Resume.uploaded_at.desc()).all()
    
    # Initialize service for templates
    service = ResumeBuilder(current_user.id)
    templates = service.get_templates()
    
    # Build a lightweight prefill dict to pass into the template (avoids extra client fetches)
    pd = PersonalDetails.query.filter_by(user_id=current_user.id).first()
    curr_emp = Employment.query.filter_by(user_id=current_user.id, is_current=True).first()
    skills_q = KeySkill.query.filter_by(user_id=current_user.id).all()
    summary = ProfileSummary.query.filter_by(user_id=current_user.id).first()
    career = CareerProfile.query.filter_by(user_id=current_user.id).first()

    prefill = {
        'full_name': pd.full_name if pd else '',
        'phone': pd.phone if pd else '',
        'city': pd.city if pd else '',
        'country': pd.country if pd else '',
        'job_title': curr_emp.job_title if curr_emp else '',
        'company_name': curr_emp.company_name if curr_emp else '',
        'email': current_user.email,
        'picture_url': url_for('static', filename=profile.profile_picture_path) if profile and profile.profile_picture_path else '',
        'skills': [s.skill_name for s in skills_q] if skills_q else [],
        'summary': summary.summary if summary else '',
        'notice_period': career.notice_period_days if career else '',
    }

    return render_template('resumes/builder.html', 
                         profile=profile, 
                         resumes=resumes,
                         templates=templates,
                         prefill=prefill)

@bp.route('/templates', methods=['GET'])
@login_required
def templates_list():
    """
    List all available resume templates for the user to choose from.
    """
    service = ResumeBuilder(current_user.id)
    templates = service.get_templates()
    return render_template('resumes/templates.html', templates=templates)

@bp.route('/generate', methods=['POST'])
@login_required
@rate_limit(limit=5, period=60) # Tighter limit for heavy generation
@credit_required('resume_generation')
async def generate_resume():
    """
    API endpoint to generate a new resume using AI.
    """
    data = request.json
    target_role = data.get('target_role')
    tone = data.get('tone', 'professional')
    
    profile = UserProfile.query.filter_by(user_id=current_user.id).first()
    
    # Budget management handled internally by ResumeBuilder via AIMeteringService
    
    # Prepare profile data for AI
    profile_data = {
        "skills": profile.skills if profile and profile.skills else "",
        "experience": 5, # Default or we could extract more info here
        "preferred_roles": target_role,
        "bio": profile.bio if profile and profile.bio else ""
    }
    
    try:
        builder = ResumeBuilder(current_user.id)
        resume_json, prompt_version_id = await builder.generate_full_resume(profile_data, target_role, tone)
        
        # Credits consumed internally

        # Save to DB
        new_resume = Resume(
            user_id=current_user.id,
            title=f"AI Generated - {target_role}",
            content_json=json.dumps(resume_json),
            is_generated=True,
            is_primary=False,
            prompt_version_id=prompt_version_id
        )
        db.session.add(new_resume)
        db.session.commit()

        # Log Initial Decision
        ResumeDecisionLogService.log_decision(
            new_resume.id,
            'generation_logic',
            f"Generated resume for {target_role}",
            f"Applied '{tone}' tone and inferred career intent to highlight relevant skills from bio."
        )
        
        return jsonify({
            'success': True, 
            'resume_id': new_resume.id,
            'data': resume_json,
            'warnings': ExperienceValidatorService.validate_experience(resume_json.get('experience', []))
        })
        
    except Exception as e:
        logger.error(f"Resume generation error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': f"Generation failed: {str(e)}"}), 500

@bp.route('/optimize/<int:resume_id>', methods=['POST'])
@login_required
@rate_limit(limit=10, period=60)
@credit_required('resume_optimization')
async def optimize_resume(resume_id):
    """
    API endpoint to optimize a resume for a job using AI.
    """
    data = request.json
    job_description = data.get('job_description')
    job_id = data.get('job_id')
    
    if not job_description:
        return jsonify({'success': False, 'message': 'Job description is required.'}), 400
        
    try:
        builder = ResumeBuilder(current_user.id)
        optimization_result = await builder.optimize_for_job(resume_id, job_description)
        
        # Persist optimization result
        opt = ResumeOptimization(
            resume_id=resume_id,
            job_id=job_id,
            optimized_content=json.dumps(optimization_result.get('tailored_summary', '')),
            ats_score=optimization_result.get('ats_score', 0),
            missing_keywords=",".join(optimization_result.get('missing_keywords', [])),
            suggestions=",".join(optimization_result.get('suggestions', [])),
            prompt_version_id=optimization_result.get('prompt_version_id')
        )
        db.session.add(opt)
        db.session.commit()
        
        # Log Optimization Decisions
        ResumeDecisionLogService.log_optimization_results(resume_id, optimization_result)
        
        return jsonify({
            'success': True,
            'optimization_id': opt.id,
            'data': optimization_result
        })
        
    except Exception as e:
        logger.error(f"Optimization error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/update/<int:resume_id>', methods=['POST'])
@login_required
def update_resume(resume_id):
    """Save edits to an existing resume"""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
    
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided.'}), 400
            
        # Sign the resume data for integrity
        data = ResumeIntegrityService.sign_resume(data)
        
        resume.content_json = json.dumps(data)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Resume updated successfully.'})
    except Exception as e:
        logger.error(f"Error updating resume: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/analyze/<int:resume_id>', methods=['POST'])
@login_required
@rate_limit(limit=10, period=60)
@credit_required('resume_optimization')
async def analyze_resume(resume_id):
    """AI analysis for ATS scoring and keyword suggestions"""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
    
    # Budget management handled internally
        
    data = request.json
    job_description = data.get('job_description', '')
    
    try:
        builder = ResumeBuilder(current_user.id)
        analysis = await builder.optimize_for_job(resume.id, job_description)
        
        # Add coherence check
        experience = resume_data.get('experience', []) if isinstance(resume_data, dict) else []
        coherence_warnings = ExperienceValidatorService.validate_experience(experience)
        
        analysis['coherence_warnings'] = coherence_warnings
        
        # Add bullet quality analysis (limited to top 5 for speed)
        top_experience = experience[:2]
        bullet_analysis = await BulletScoringService.score_experience(top_experience)
        analysis['bullet_analysis'] = bullet_analysis
        
        # Add ATS Simulation
        ats_sim = ATSSimulatorService.simulate_parse(resume_data, job_description)
        analysis['ats_simulation'] = ats_sim
        
        # Add Recruiter Scan (Human eye simulation)
        recruiter_scan = await RecruiterScanService.simulate_scan(resume_data)
        analysis['recruiter_scan'] = recruiter_scan

        # Add Bias & Legal Risk Analysis
        bias_warnings = BiasDetectionService.analyze_bias(resume_data)
        analysis['bias_risk'] = bias_warnings
        
        # Budget consumed internally
        
        return jsonify({
            'success': True,
            'data': analysis
        })
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/improve-text', methods=['POST'])
@login_required
@rate_limit(limit=15, period=60) # Relaxed for inline micro-tasks
@credit_required('resume_coach')
async def improve_text():
    """AI improvement for a specific text block"""
    data = request.json
    text = data.get('text', '')
    context = data.get('context', 'text section')
    
    # Budget management handled internally by AIMeteringService
    
    try:
        from app.services.hybrid_enhancement import HybridEnhancementService
        improved_text, was_ai_used = await HybridEnhancementService.improve_bullet(current_user.id, text, context)
        
        # 2. Credits consumed internally if AI was actually called
        if was_ai_used:
            # Internal logging handled by AIMeteringService
            
            # 3. Log Decision (If we have a resume context)
            resume_id = data.get('resume_id')
            if resume_id:
                ResumeDecisionLogService.log_decision(
                    resume_id,
                    'bullet_rewritten',
                    f"Improved {context}",
                    f"Refined text to improve professional tone and impact based on career consultant standards."
                )

        return jsonify({
            'success': True,
            'data': improved_text,
            'was_ai_used': was_ai_used
        })
    except Exception as e:
        logger.error(f"Improve text error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/set-primary/<int:resume_id>', methods=['POST'])
@login_required
def set_primary(resume_id):
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
        
    # Unset others
    Resume.query.filter_by(user_id=current_user.id).update({Resume.is_primary: False})
    
    resume.is_primary = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Primary resume updated.'})

@bp.route('/delete/<int:resume_id>', methods=['POST'])
@login_required
def delete_resume(resume_id):
    try:
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
        if not resume:
            return jsonify({'success': False, 'message': 'Resume not found.'}), 404
        
        # Delete related optimizations first (to handle foreign key constraints)
        ResumeOptimization.query.filter_by(resume_id=resume_id).delete()
        
        # Delete the resume
        db.session.delete(resume)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Resume deleted successfully.'})
        
    except Exception as e:
        logger.error(f"Error deleting resume {resume_id}: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Failed to delete resume: {str(e)}'}), 500

@bp.route('/view/<int:resume_id>', methods=['GET'])
@login_required
def view_resume(resume_id):
    """Get resume data for viewing"""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
    
    try:
        resume_data = {}
        if resume.content_json:
            resume_data = json.loads(resume.content_json)
        elif resume.file_path:
            # Auto-parse if physical file exists but JSON doesn't
            from app.services.resume_parser import ResumeParserService
            parse_result = ResumeParserService.parse_resume_file(resume.file_path)
            if parse_result['success']:
                extracted = parse_result['data']
                # Convert parser format to builder format
                resume_data = {
                    'header': {
                        'full_name': extracted.get('full_name') or current_user.full_name or "My Name",
                        'title': "Target Role",
                        'email': extracted.get('email') or current_user.email,
                        'phone': extracted.get('phone') or "",
                        'location': extracted.get('location') or ""
                    },
                    'summary': extracted.get('summary') or "",
                    'skills': extracted.get('skills') or [],
                    'experience': [],
                    'education': []
                }
                
                # Map experience
                for exp in extracted.get('experience', []):
                    resume_data['experience'].append({
                        'role': exp.get('job_title', 'Role'),
                        'company': exp.get('company_name', 'Company'),
                        'duration': f"{exp.get('start_year', '')} - {exp.get('end_year', 'Present')}" if exp.get('start_year') else "Duration",
                        'achievements': [f"Key responsibility at {exp.get('company_name')}"]
                    })
                
                # Map education
                for edu in extracted.get('education', []):
                    resume_data['education'].append({
                        'degree': edu.get('degree', 'Degree'),
                        'institution': edu.get('institution', 'Institution'),
                        'year': str(edu.get('end_year', 'Year'))
                    })
                
                # Save it back to cache it
                resume.content_json = json.dumps(resume_data)
                db.session.commit()
        
        # Smart Backfill: content_json might have empty fields, so we fill them from Profile
        header = resume_data.get('header', {})
        
        # Helper to get PersonalDetails
        pd = current_user.personal_details
        
        if not header.get('full_name'):
            header['full_name'] = (pd.full_name if pd and pd.full_name else current_user.email.split('@')[0].title())
            
        if not header.get('email'):
            header['email'] = current_user.email
            
        if not header.get('phone') and pd and pd.phone:
            header['phone'] = pd.phone
            
        if not header.get('location'):
            # Use the model property logic for location
            header['location'] = current_user.current_location
            
        if not header.get('title'):
            curr_job = current_user.current_job
            if curr_job and curr_job.job_title:
                header['title'] = curr_job.job_title
                
        resume_data['header'] = header

        # Ensure minimum structure to prevent JS crashes
        if 'skills' not in resume_data: resume_data['skills'] = []
        if 'experience' not in resume_data: resume_data['experience'] = []
        if 'education' not in resume_data: resume_data['education'] = []

        # Verify Integrity
        is_authentic, integrity_meta = ResumeIntegrityService.verify_integrity(resume_data)
        
        return jsonify({
            'success': True,
            'data': resume_data,
            'resume_id': resume.id,
            'integrity': {
                'is_authentic': is_authentic,
                'metadata': integrity_meta
            },
            'title': resume.title or "My Resume",
            'is_primary': resume.is_primary
        })
    except Exception as e:
        logger.error(f"Error viewing resume: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/decision-logs/<int:resume_id>', methods=['GET'])
@login_required
def get_decision_logs(resume_id):
    """Retrieves AI decision logs for explainability."""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
        
    logs = ResumeDecisionLogService.get_logs(resume_id)
    return jsonify({
        'success': True,
        'logs': [
            {
                'type': log.action_type,
                'summary': log.decision_summary,
                'rationale': log.rationale,
                'timestamp': log.timestamp.isoformat()
            } for log in logs
        ]
    })

@bp.route('/download/<int:resume_id>', methods=['GET'])
@login_required
def download_resume_pdf(resume_id):
    """Download resume as PDF"""
    from flask import send_file, make_response
    from app.resumes.generator import ResumeGenerator
    from app.services.pii_service import PIIService
    import os
    import tempfile
    
    export_mode = request.args.get('mode', 'full') # full, recruiter-safe, public
    
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
    
    try:
        resume_data = json.loads(resume.content_json) if resume.content_json else {}
        
        # Apply PII Redaction
        resume_data = PIIService.redact_resume(resume_data, mode=export_mode)
        
        # Generate PDF
        generator = ResumeGenerator()
        
        # Select template based on resume data
        template_id = resume_data.get('template_id', 'modern')
        template_name = f"{template_id}.jinja"
        
        # Create temp file for PDF
        temp_dir = tempfile.gettempdir()
        pdf_filename = f"resume_{resume_id}_{current_user.id}.pdf"
        pdf_path = os.path.join(temp_dir, pdf_filename)
        
        # Generate the PDF with the selected template
        success = generator.export_pdf(resume_data, pdf_path, template_name=template_name)
        
        if success and os.path.exists(pdf_path):
            # Send file and clean up
            response = send_file(
                pdf_path,
                as_attachment=True,
                download_name=f"Resume_{resume_data.get('header', {}).get('full_name', 'User').replace(' ', '_')}.pdf",
                mimetype='application/pdf'
            )
            
            # Schedule file deletion after sending
            @response.call_on_close
            def cleanup():
                try:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                except:
                    pass
            
            return response
        else:
            return jsonify({'success': False, 'message': 'Failed to generate PDF'}), 500
            
    except Exception as e:
        logger.error(f"Error downloading resume PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500
@bp.route('/health-score/<int:resume_id>', methods=['POST'])
@login_required
def get_health_score(resume_id):
    """Calculates comprehensive resume health score."""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
    
    data = request.json
    job_description = data.get('job_description')
    
    try:
        resume_data = json.loads(resume.content_json) if resume.content_json else {}
        
        from app.services.resume_health import ResumeHealthService
        health_report = ResumeHealthService.calculate_health_score(resume_data, job_description)
        
        return jsonify({
            'success': True,
            'health': health_report
        })
    except Exception as e:
        logger.error(f"Health score calculation failed: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/validate-edit', methods=['POST'])
@login_required
def validate_edit():
    """Real-time validation for inline edits."""
    data = request.json
    field_path = data.get('field_path', '')
    value = data.get('value', '')
    context = data.get('context', {})
    
    from app.services.inline_edit import InlineEditService
    warnings = InlineEditService.validate_content(field_path, value, context)
    
    return jsonify({
        'success': True,
        'warnings': warnings
    })

@bp.route('/log-action', methods=['POST'])
@login_required
def log_user_action():
    """Logs user feedback/rejection of AI output."""
    data = request.json
    action_type = data.get('action_type') # e.g., 'ai_rejected'
    resume_id = data.get('resume_id')
    original_text = data.get('original_ai_text')
    final_text = data.get('final_user_text')
    
    try:
        from app.models.user_action_log import UserActionLog
        log = UserActionLog(
            user_id=current_user.id,
            resume_id=resume_id,
            action_type=action_type,
            original_ai_text=original_text,
            final_user_text=final_text
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to log user action: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# PREMIUM FEATURES (Premium + Enterprise only)
# ============================================================================

@bp.route('/recruiter-persona/<int:resume_id>', methods=['POST'])
@login_required
def analyze_recruiter_persona(resume_id):
    """Analyze resume from recruiter persona perspective (Premium feature)."""
    from app.services.feature_flags import require_premium
    from app.services.premium_features import PremiumFeaturesService
    
    # Check premium access
    if not current_user.subscription or not current_user.subscription.is_premium():
        return jsonify({
            'success': False,
            'error': 'premium_required',
            'message': 'Recruiter Personas require a Premium or Enterprise subscription.',
            'upgrade_url': '/pricing'
        }), 403
    
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
    
    data = request.json
    persona_type = data.get('persona_type', 'tech_startup')
    
    try:
        resume_data = json.loads(resume.content_json) if resume.content_json else {}
        analysis = PremiumFeaturesService.analyze_with_persona(resume_data, persona_type)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        logger.error(f"Recruiter persona analysis failed: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/interview-probability/<int:resume_id>', methods=['POST'])
@login_required
def calculate_interview_probability(resume_id):
    """Calculate interview probability score (Premium feature)."""
    from app.services.premium_features import PremiumFeaturesService
    
    # Check premium access
    if not current_user.subscription or not current_user.subscription.is_premium():
        return jsonify({
            'success': False,
            'error': 'premium_required',
            'message': 'Interview Probability requires a Premium or Enterprise subscription.',
            'upgrade_url': '/pricing'
        }), 403
    
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
    
    data = request.json
    job_description = data.get('job_description')
    
    try:
        resume_data = json.loads(resume.content_json) if resume.content_json else {}
        probability = PremiumFeaturesService.calculate_interview_probability(resume_data, job_description)
        
        return jsonify({
            'success': True,
            'probability': probability
        })
    except Exception as e:
        logger.error(f"Interview probability calculation failed: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/analytics', methods=['GET'])
@login_required
def get_resume_analytics():
    """Get advanced resume analytics (Premium feature)."""
    from app.services.premium_features import PremiumFeaturesService
    
    # Check premium access
    if not current_user.subscription or not current_user.subscription.is_premium():
        return jsonify({
            'success': False,
            'error': 'premium_required',
            'message': 'Resume Analytics require a Premium or Enterprise subscription.',
            'upgrade_url': '/pricing'
        }), 403
    
    try:
        analytics = PremiumFeaturesService.generate_resume_analytics(current_user.id)
        
        return jsonify({
            'success': True,
            'analytics': analytics
        })
    except Exception as e:
        logger.error(f"Analytics generation failed: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# ENTERPRISE FEATURES (Enterprise only)
# ============================================================================

@bp.route('/bulk-upload', methods=['POST'])
@login_required
def bulk_upload_resumes():
    """Upload multiple resumes at once (Enterprise feature)."""
    from app.services.enterprise_features import EnterpriseFeaturesService
    
    # Check enterprise access
    if not current_user.subscription or not current_user.subscription.is_enterprise():
        return jsonify({
            'success': False,
            'error': 'enterprise_required',
            'message': 'Bulk Upload is exclusive to Enterprise subscribers.',
            'upgrade_url': '/pricing'
        }), 403
    
    if 'files' not in request.files:
        return jsonify({'success': False, 'message': 'No files provided.'}), 400
    
    files = request.files.getlist('files')
    
    # Validate limits
    validation = EnterpriseFeaturesService.validate_bulk_upload_limit(current_user.id, len(files))
    if not validation['allowed']:
        return jsonify({'success': False, 'message': validation['message']}), 400
    
    try:
        results = EnterpriseFeaturesService.process_bulk_upload(files, current_user.id)
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logger.error(f"Bulk upload failed: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/export-compliant/<int:resume_id>', methods=['POST'])
@login_required
def export_compliant_resume(resume_id):
    """Export resume with compliance standards (Enterprise feature)."""
    from app.services.enterprise_features import EnterpriseFeaturesService
    
    # Check enterprise access
    if not current_user.subscription or not current_user.subscription.is_enterprise():
        return jsonify({
            'success': False,
            'error': 'enterprise_required',
            'message': 'Compliance Mode is exclusive to Enterprise subscribers.',
            'upgrade_url': '/pricing'
        }), 403
    
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
    
    data = request.json
    compliance_standard = data.get('standard', 'gdpr')  # gdpr, sox, hipaa
    
    try:
        resume_data = json.loads(resume.content_json) if resume.content_json else {}
        compliant = EnterpriseFeaturesService.apply_compliance_mode(resume_data, compliance_standard)
        
        return jsonify({
            'success': True,
            'compliant_resume': compliant
        })
    except Exception as e:
        logger.error(f"Compliance export failed: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/export-white-label/<int:resume_id>', methods=['POST'])
@login_required
def export_white_label_resume(resume_id):
    """Export resume with white-label branding (Enterprise feature)."""
    from app.services.enterprise_features import EnterpriseFeaturesService
    
    # Check enterprise access
    if not current_user.subscription or not current_user.subscription.is_enterprise():
        return jsonify({
            'success': False,
            'error': 'enterprise_required',
            'message': 'White-Label Exports are exclusive to Enterprise subscribers.',
            'upgrade_url': '/pricing'
        }), 403
    
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({'success': False, 'message': 'Resume not found.'}), 404
    
    data = request.json
    branding_config = data.get('branding', {})
    
    try:
        resume_data = json.loads(resume.content_json) if resume.content_json else {}
        white_label = EnterpriseFeaturesService.generate_white_label_export(resume_data, branding_config)
        
        return jsonify({
            'success': True,
            'white_label_resume': white_label
        })
    except Exception as e:
        logger.error(f"White-label export failed: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================================
# ENTERPRISE RESUME MODE (Advanced bulk processing with compliance)
# ============================================================================

@bp.route('/enterprise/bulk-process', methods=['POST'])
@login_required
def enterprise_bulk_process():
    """Process multiple resumes with compliance checks and audit logging (Enterprise feature)."""
    from app.services.enterprise_resume import EnterpriseResumeService
    
    # Check enterprise access
    if not current_user.subscription or not current_user.subscription.is_enterprise():
        return jsonify({
            'success': False,
            'error': 'enterprise_required',
            'message': 'Enterprise Resume Mode is exclusive to Enterprise subscribers.',
            'upgrade_url': '/pricing'
        }), 403
    
    data = request.json
    resumes = data.get('resumes', [])
    options = data.get('options', {})
    
    if not resumes:
        return jsonify({'success': False, 'message': 'No resumes provided.'}), 400
    
    try:
        # Process with SLA monitoring
        results = EnterpriseResumeService.process_bulk_resumes(resumes, options)
        
        # Create audit log
        EnterpriseResumeService.create_audit_log(
            action='bulk_resume_processing',
            user_id=current_user.id,
            details={
                'total_resumes': len(resumes),
                'successful': results['successful'],
                'failed': results['failed'],
                'compliance_mode': options.get('compliance_mode', False),
                'ip_address': request.remote_addr
            }
        )
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logger.error(f"Enterprise bulk processing failed: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/enterprise/compliance-report', methods=['GET'])
@login_required
def get_compliance_report():
    """Generate comprehensive compliance report (Enterprise feature)."""
    from app.services.enterprise_resume import EnterpriseResumeService
    
    # Check enterprise access
    if not current_user.subscription or not current_user.subscription.is_enterprise():
        return jsonify({
            'success': False,
            'error': 'enterprise_required',
            'message': 'Compliance Reports are exclusive to Enterprise subscribers.',
            'upgrade_url': '/pricing'
        }), 403
    
    try:
        report = EnterpriseResumeService.generate_compliance_report(current_user.id)
        
        # Create audit log
        EnterpriseResumeService.create_audit_log(
            action='compliance_report_generated',
            user_id=current_user.id,
            details={
                'total_resumes_checked': report['total_resumes'],
                'ip_address': request.remote_addr
            }
        )
        
        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        logger.error(f"Compliance report generation failed: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/enterprise/audit-logs', methods=['GET'])
@login_required
def get_audit_logs():
    """Retrieve audit logs for user (Enterprise feature)."""
    from app.models.audit_log import AuditLog
    
    # Check enterprise access
    if not current_user.subscription or not current_user.subscription.is_enterprise():
        return jsonify({
            'success': False,
            'error': 'enterprise_required',
            'message': 'Audit Logs are exclusive to Enterprise subscribers.',
            'upgrade_url': '/pricing'
        }), 403
    
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Query audit logs
        logs_query = AuditLog.query.filter_by(user_id=current_user.id).order_by(AuditLog.timestamp.desc())
        logs_paginated = logs_query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs_paginated.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': logs_paginated.total,
                'pages': logs_paginated.pages
            }
        })
    except Exception as e:
        logger.error(f"Audit log retrieval failed: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/download-wysiwyg', methods=['POST'])
@login_required
def download_resume_wysiwyg():
    """
    Generate PDF from client-side HTML to ensure exact WYSIWYG match.
    """
    try:
        from app.resumes.generator import ResumeGenerator
        data = request.json
        raw_html = data.get('html_content')
        
        if not raw_html:
            return jsonify({'success': False, 'message': 'HTML content missing'}), 400
            
        generator = ResumeGenerator()
        
        # Create temp file for PDF
        temp_dir = tempfile.gettempdir()
        import uuid
        pdf_filename = f"resume_export_{current_user.id}_{uuid.uuid4().hex}.pdf"
        pdf_path = os.path.join(temp_dir, pdf_filename)
        
        # Generate the PDF
        success = generator.export_from_raw_html(raw_html, pdf_path)
        
        if success and os.path.exists(pdf_path):
            # Send file and clean up
            response = send_file(
                pdf_path,
                as_attachment=True,
                download_name=f"Resume_Export.pdf",
                mimetype='application/pdf'
            )
            
            @response.call_on_close
            def cleanup():
                try:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                except:
                    pass
            
            return response
        else:
            msg = "Failed to generate PDF (Unknown reason)"
            if not success:
                msg = "Generator returned False"
            elif not os.path.exists(pdf_path):
                msg = f"PDF file not found at {pdf_path}"
                
            logger.error(msg)
            return jsonify({'success': False, 'message': msg}), 500
            
    except Exception as e:
        logger.error(f"Error downloading WYSIWYG PDF: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500

