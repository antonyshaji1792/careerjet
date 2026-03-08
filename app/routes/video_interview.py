import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.services.video_interview_service import VideoInterviewService
from app.models.video_interview import AIVideoInterview, AIVideoSummary
from app.extensions import db
from app.utils.credit_middleware import credit_required
from app.utils.rate_limiter import rate_limit

logger = logging.getLogger(__name__)

bp = Blueprint('video_interview', __name__, url_prefix='/video-interview')

@bp.route('/')
@login_required
def index():
    """Video Interview Hub / History"""
    interviews = AIVideoInterview.query.filter_by(user_id=current_user.id).order_by(AIVideoInterview.created_at.desc()).all()
    return render_template('video_interview/index.html', interviews=interviews)

@bp.route('/setup')
@login_required
def setup():
    """The Green Room / Setup Page"""
    return render_template('video_interview/setup.html')

@bp.route('/session/<int:session_id>')
@login_required
def session_stage(session_id):
    """The actual interview stage"""
    interview = AIVideoInterview.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    
    if interview.status == 'completed':
        return redirect(url_for('video_interview.results', session_id=session_id))
        
    session_data = {
        "session_id": interview.id,
        "job_title": interview.job_title,
        "persona": interview.persona_id,
        "camera_enabled": interview.camera_enabled,
        "questions": [{"id": q.id, "question": q.question_text} for q in interview.questions]
    }
    return render_template('video_interview/session.html', session_data=session_data)

@bp.route('/start', methods=['POST'])
@login_required
@rate_limit(limit=5, period=60)
@credit_required('video_interview_evaluation')
async def start_session():

    """Initializes the session and returns the stage template"""
    job_title = request.form.get('job_title', 'General Position')
    persona = request.form.get('persona', 'alex')
    difficulty = request.form.get('difficulty', 'medium')
    camera_enabled = True # Always enable for the immersive stage

    service = VideoInterviewService(current_user.id)
    try:
        session_data = await service.initialize_session(
            job_title=job_title,
            persona=persona,
            difficulty=difficulty,
            camera_enabled=camera_enabled
        )
        return render_template('video_interview/session.html', session_data=session_data)
    except Exception as e:
        logger.error(f"Error starting video session: {str(e)}")
        flash(f"Could not initialize interview: {str(e)}", "danger")
        return redirect(url_for('video_interview.setup'))

@bp.route('/api/v1/answer', methods=['POST'])
@login_required
@rate_limit(limit=20, period=60)
@credit_required('video_interview_evaluation')
async def submit_answer():

    """API endpoint to process a transcript and return an AI reaction"""
    data = request.json
    session_id = data.get('session_id')
    question_id = data.get('question_id')
    transcript = data.get('transcript', '')
    metadata = data.get('metadata', {})

    if not session_id or not question_id:
        return jsonify({"error": "Missing session_id or question_id"}), 400

    service = VideoInterviewService(current_user.id)
    try:
        # 1. Process the answer and get immediate reaction
        result = await service.process_answer(session_id, question_id, transcript, metadata)
        
        # 2. Return the reaction and next steps
        return jsonify({
            "status": "success",
            "evaluation_id": result.get('evaluation_id'),
            "reaction_text": result.get('reaction_text', 'Thank you. Let\'s move to the next question.'),
            "score_hint": result.get('score', 0)
        })
    except Exception as e:
        logger.error(f"Error processing answer for session {session_id}: {str(e)}")
        return jsonify({"error": "Internal server error during evaluation"}), 500

@bp.route('/api/v1/complete/<int:session_id>', methods=['POST'])
@login_required
async def api_complete_session(session_id):
    """Explicitly signals session completion and triggers report generation"""
    service = VideoInterviewService(current_user.id)
    try:
        summary = await service.generate_final_report(session_id)
        return jsonify({
            "status": "completed",
            "session_id": session_id,
            "redirect_url": url_for('video_interview.results', session_id=session_id)
        })
    except Exception as e:
        logger.error(f"Error completing session {session_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/results/<int:session_id>')
@login_required
async def results(session_id):
    """Intermediate results / completion screen"""
    interview = AIVideoInterview.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    
    service = VideoInterviewService(current_user.id)
    summary = await service.generate_final_report(session_id)
    
    if not summary:
        # Fallback if no answers provided
        return redirect(url_for('video_interview.index'))

    result_data = {
        "session_id": session_id,
        "readiness_score": int(interview.overall_score or 0),
        "summary": summary.summary_text,
        "top_strength": summary.key_strengths_json[0] if summary.key_strengths_json else "N/A",
        "top_gap": summary.areas_for_improvement_json[0] if summary.areas_for_improvement_json else "N/A"
    }
    
    return render_template('video_interview/complete.html', result=result_data)

@bp.route('/report/<int:session_id>')
@login_required
def report(session_id):
    """Full detailed analytical report"""
    interview = AIVideoInterview.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    summary = AIVideoSummary.query.filter_by(interview_id=session_id).first_or_404()
    
    # Structure data for Report Template
    report_data = {
        "job_title": interview.job_title,
        "persona": interview.persona_id,
        "created_at": interview.created_at,
        "overall_score": int(interview.overall_score or 0),
        "video_url": interview.video_url,
        "metrics": {
            "pacing": int(summary.average_pace_wpm),
            "confidence": int(summary.average_confidence * 100),
            "filler_count": 0 # Placeholder for now
        },
        "strengths": summary.key_strengths_json,
        "gaps": summary.areas_for_improvement_json,
        "claims": [
            # Mock claims for the verification table
            {"skill": "Communication", "claimed_level": "Expert", "actual_score": 85},
            {"skill": "Problem Solving", "claimed_level": "Senior", "actual_score": 70}
        ],
        "radar_data": {
            "labels": ["Technical", "Communication", "Problem Solving", "Cultural Fit", "Leadership"],
            "values": [80, 90, 70, 85, 60]
        },
        "turns": []
    }
    
    # Build turns
    for q in interview.questions:
        if q.answer:
            report_data["turns"].append({
                "question": q.question_text,
                "transcript": q.answer.audio_transcript,
                "feedback": q.answer.evaluation.feedback_text if q.answer.evaluation else "No feedback",
                "tags": [q.category]
            })

    return render_template('video_interview/report.html', report=report_data)

@bp.route('/delete/<int:session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    """Deletes a video interview session and all its associated data"""
    interview = AIVideoInterview.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    
    try:
        db.session.delete(interview)
        db.session.commit()
        flash("Interview history deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting session {session_id}: {str(e)}")
        flash("Could not delete interview history.", "danger")
        
    return redirect(url_for('video_interview.index'))

@bp.route('/delete-all', methods=['POST'])
@login_required
def delete_all_sessions():
    """Deletes all video interview sessions for the current user"""
    try:
        AIVideoInterview.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        flash("All interview history has been cleared.", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting all sessions for user {current_user.id}: {str(e)}")
        flash("Could not clear interview history.", "danger")
        
    return redirect(url_for('video_interview.index'))

@bp.route('/upload-video/<int:session_id>', methods=['POST'])
@login_required
def upload_video(session_id):
    """Saves the recorded video for a session"""
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
        
    video_file = request.files['video']
    interview = AIVideoInterview.query.filter_by(id=session_id, user_id=current_user.id).first_or_404()
    
    import os
    from flask import current_app
    
    upload_folder = os.path.join(current_app.static_folder, 'uploads', 'video_interviews')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    filename = f"interview_{session_id}_{current_user.id}.webm"
    filepath = os.path.join(upload_folder, filename)
    video_file.save(filepath)
    
    # Store relative path for web access
    interview.video_url = f"/static/uploads/video_interviews/{filename}"
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "video_url": interview.video_url
    })
