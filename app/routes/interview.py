from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils.credit_middleware import credit_required
from app.services.interview_service import InterviewService
import uuid

bp = Blueprint('interview', __name__, url_prefix='/interview')

@bp.route('/')
@login_required
def index():
    """Interview Prep landing page."""
    return render_template('interview/index.html')

@bp.route('/setup', methods=['POST'])
@login_required
@credit_required('interview_coach')
async def setup_session():
    """Initialize a new interview session."""
    job_title = request.form.get('job_title')
    company = request.form.get('company')
    description = request.form.get('description')
    difficulty = request.form.get('difficulty', 'medium')
    
    if not job_title:
        flash('Job Title is required', 'danger')
        return redirect(url_for('interview.index'))

    # Store session metadata
    session_id = str(uuid.uuid4())
    questions = await InterviewService.generate_questions(current_user.id, job_title, company, description, difficulty)
    
    # Store in Flask session (client-side cookie storage might be too small, but trying primarily)
    # Ideally use server-side cache like Redis or DB.
    # For now, we'll store minimal data and hope the questions list isn't too huge.
    session['interview_session'] = {
        'id': session_id,
        'job_title': job_title,
        'company': company,
        'difficulty': difficulty,
        'questions': questions,
        'current_index': 0,
        'answers': []
    }
    
    return redirect(url_for('interview.session_view'))

@bp.route('/session')
@login_required
def session_view():
    """Active interview session view."""
    interview_data = session.get('interview_session')
    if not interview_data:
        flash('No active interview session found.', 'warning')
        return redirect(url_for('interview.index'))
        
    current_index = interview_data.get('current_index', 0)
    questions = interview_data.get('questions', [])
    
    if current_index >= len(questions):
        return redirect(url_for('interview.results'))
        
    current_q = questions[current_index]
    
    return render_template('interview/session.html', 
                           question=current_q, 
                           index=current_index + 1, 
                           total=len(questions),
                           job_title=interview_data['job_title'])

@bp.route('/evaluate', methods=['POST'])
@login_required
@credit_required('interview_coach')
async def evaluate_answer():
    """AJAX endpoint to evaluate an answer."""
    interview_data = session.get('interview_session')
    if not interview_data:
        return jsonify({'error': 'No session'}), 400
        
    data = request.get_json()
    user_answer = data.get('answer')
    question_text = data.get('question')
    
    if not user_answer:
        return jsonify({'error': 'Answer cannot be empty'}), 400

    evaluation = await InterviewService.evaluate_answer(
        current_user.id,
        question_text, 
        user_answer, 
        interview_data['job_title']
    )
    
    # Store result in session
    # We must re-assign to session to persist updates in some Flask session interfaces
    interview_data['answers'].append({
        'question': question_text,
        'answer': user_answer,
        'evaluation': evaluation
    })
    
    # Move to next question
    interview_data['current_index'] += 1
    session['interview_session'] = interview_data
    
    return jsonify(evaluation)

@bp.route('/results')
@login_required
def results():
    """Show session results."""
    interview_data = session.get('interview_session')
    if not interview_data:
        return redirect(url_for('interview.index'))
        
    return render_template('interview/results.html', session_data=interview_data)

@bp.route('/reset')
@login_required
def reset():
    session.pop('interview_session', None)
    return redirect(url_for('interview.index'))
