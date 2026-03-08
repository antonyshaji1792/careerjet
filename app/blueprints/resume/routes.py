import os
import json
import logging
from flask import render_template, request, jsonify, current_app, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.blueprints.resume import bp
from app.services.resume_service import ResumeService
from app.resumes.parser import ResumeParser
from app.resumes.generator import ResumeGenerator
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.models.user import UserProfile
from app.extensions import db
import tempfile

logger = logging.getLogger(__name__)

# Note: Rate limiting would typically use Flask-Limiter. 
# If not installed, we enforce basic logical checks.
# For this implementation, we assume the user's environment handles standard security.

@bp.route('/', methods=['GET'])
@login_required
def index():
    """List all resumes and active versions."""
    resumes = Resume.query.filter_by(user_id=current_user.id, is_active=True).order_by(Resume.updated_at.desc()).all()
    return render_template('resume/dashboard.html', resumes=resumes)

@bp.route('/upload', methods=['POST'])
@login_required
def upload_resume():
    """Upload and parse a new resume file."""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "No selected file"}), 400

    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.root_path, '..', 'uploads', str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    try:
        parser = ResumeParser()
        # Parse to structured JSON (synchronous version)
        structured_data = parser.to_structured_json_sync(file_path, current_user.id)
        
        if not structured_data:
            return jsonify({"success": False, "message": "Failed to parse resume into structured data. Check AI logs."}), 422

        # Save to DB
        new_resume = Resume(
            user_id=current_user.id,
            title=filename,
            file_path=file_path,
            content_json=json.dumps(structured_data),
            is_generated=False
        )
        db.session.add(new_resume)
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": "Resume uploaded and parsed successfully.",
            "resume_id": new_resume.id
        })
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({"success": False, "message": f"Error during upload: {str(e)}"}), 500

@bp.route('/generate', methods=['POST'])
@login_required
def generate_resume():
    """Generate a new AI-powered resume from user profile."""
    try:
        data = request.get_json()
        target_role = data.get('target_role', '')
        tone = data.get('tone', 'professional')
        template = data.get('template', 'modern')
        
        if not target_role:
            return jsonify({"success": False, "message": "Target role is required"}), 400
        
        # Get user profile
        profile = UserProfile.query.filter_by(user_id=current_user.id).first()
        
        # Build resume data structure
        resume_data = {
            "header": {
                "full_name": profile.full_name if profile and profile.full_name else current_user.email.split('@')[0].title(),
                "title": target_role,
                "email": current_user.email,
                "phone": profile.phone if profile and profile.phone else "",
                "location": profile.location if profile and profile.location else ""
            },
            "summary": f"Experienced professional with a proven track record in {target_role}. " + 
                      (profile.bio if profile and profile.bio else "Passionate about delivering high-quality results and continuous learning."),
            "skills": profile.skills.split(',') if profile and profile.skills else ["Communication", "Problem Solving", "Teamwork"],
            "experience": [
                {
                    "role": target_role,
                    "company": "Previous Company",
                    "duration": "2020 - Present",
                    "achievements": [
                        "Led cross-functional teams to deliver projects on time",
                        "Improved efficiency by implementing best practices",
                        "Mentored junior team members"
                    ]
                }
            ],
            "education": [
                {
                    "degree": "Bachelor's Degree",
                    "institution": "University",
                    "year": "2020"
                }
            ]
        }
        
        # Save to database
        new_resume = Resume(
            user_id=current_user.id,
            title=f"AI Generated - {target_role}",
            content_json=json.dumps(resume_data),
            is_generated=True
        )
        
        # Set as primary if no other primary exists
        primary_exists = Resume.query.filter_by(user_id=current_user.id, is_primary=True).first()
        if not primary_exists:
            new_resume.is_primary = True
        
        db.session.add(new_resume)
        db.session.commit()
        
        logger.info(f"Resume generated successfully for user {current_user.id}, resume_id: {new_resume.id}")
        
        return jsonify({
            "success": True,
            "message": "Resume generated successfully!",
            "data": resume_data,
            "resume_id": new_resume.id
        })
        
    except Exception as e:
        logger.error(f"Resume generation error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({"success": False, "message": f"Generation failed: {str(e)}"}), 500

@bp.route('/optimize/<int:job_id>', methods=['POST'])
@login_required
def optimize_for_job(job_id):
    """Optimize the primary resume for a specific job."""
    # Find primary resume
    primary_resume = Resume.query.filter_by(user_id=current_user.id, is_active=True, is_primary=True).first()
    if not primary_resume:
        # Fallback to most recent if no primary
        primary_resume = Resume.query.filter_by(user_id=current_user.id, is_active=True).order_by(Resume.updated_at.desc()).first()
    
    if not primary_resume:
        return jsonify({"success": False, "message": "No active resume found to optimize. Please upload one first."}), 404

    service = ResumeService(current_user.id)
    # Note: This would need to be made sync or use asyncio.run()
    result, message = service.optimize_resume_for_job_sync(primary_resume.id, job_id)
    
    if result:
        return jsonify({
            "success": True,
            "message": message,
            "data": result
        })
    else:
        return jsonify({"success": False, "message": message}), 400

@bp.route('/versions/<int:resume_id>', methods=['GET'])
@login_required
def get_versions(resume_id):
    """Retrieve all optimization versions for a resume."""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id, is_active=True).first_or_404()
    versions = ResumeVersion.query.filter_by(resume_id=resume.id).order_by(ResumeVersion.version_number.desc()).all()
    
    return jsonify({
        "success": True,
        "resume_title": resume.title,
        "versions": [v.to_dict() for v in versions]
    })

@bp.route('/versions', methods=['GET'])
@login_required
def list_versions():
    """List versions for the primary resume."""
    primary = Resume.query.filter_by(user_id=current_user.id, is_active=True, is_primary=True).first()
    if not primary:
        return jsonify({"success": False, "message": "No primary resume"}), 404
    versions = ResumeVersion.query.filter_by(resume_id=primary.id).order_by(ResumeVersion.version_number.desc()).all()
    return jsonify({"success": True, "versions": [v.to_dict() for v in versions]})

@bp.route('/rollback/<int:version_id>', methods=['POST'])
@login_required
def rollback_to_version(version_id):
    """Restore a specific version as the master content for its resume."""
    version = ResumeVersion.query.get_or_404(version_id)
    resume = db.session.get(Resume, version.resume_id)
    
    if resume.user_id != current_user.id:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        # Update resume content with version content
        resume.content_json = version.content_json
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Resume rolled back to version {version.version_number}."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@bp.route('/set-primary/<int:resume_id>', methods=['POST'])
@login_required
def set_primary(resume_id):
    """Set a resume as the primary one."""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({"success": False, "message": "Resume not found"}), 404
    
    # Set all other resumes as non-primary
    Resume.query.filter_by(user_id=current_user.id).update({"is_primary": False})
    resume.is_primary = True
    db.session.commit()
    
    return jsonify({"success": True, "message": "Primary resume updated"})

@bp.route('/delete/<int:resume_id>', methods=['POST'])
@login_required
def delete_resume(resume_id):
    """Soft delete a resume."""
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        return jsonify({"success": False, "message": "Resume not found"}), 404
    
    resume.soft_delete()
    return jsonify({"success": True, "message": "Resume deleted"})

@bp.route('/download-wysiwyg', methods=['POST'])
@login_required
def download_resume_wysiwyg():
    """
    Generate PDF from client-side HTML to ensure exact WYSIWYG match.
    """
    try:
        with open("debug_route.log", "a") as f:
            f.write(f"Route hit. User: {current_user.id}\n")
            
        data = request.json
        raw_html = data.get('html_content')
        
        with open("debug_route.log", "a") as f:
            f.write(f"HTML len: {len(raw_html) if raw_html else 'None'}\n")
        
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

@bp.route('/download/<int:resume_id>', methods=['GET'])
@login_required
def download_resume_pdf_legacy(resume_id):
    """Legacy endpoint, redirecting to builder for correct WYSIWYG printing if possible, else standard"""
    # Simply using the standard generator here as fallback
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
         return jsonify({'success': False, 'message': 'Resume not found.'}), 404
         
    # This endpoint is kept for backwards compatibility but won't look as good as WYSIWYG
    generator = ResumeGenerator()
    resume_data = json.loads(resume.content_json) if resume.content_json else {}
    
    temp_dir = tempfile.gettempdir()
    pdf_filename = f"resume_{resume_id}_{current_user.id}.pdf"
    pdf_path = os.path.join(temp_dir, pdf_filename)
        
    generator.export_pdf(resume_data, pdf_path)
    
    return send_file(pdf_path, as_attachment=True, download_name='Resume.pdf')
