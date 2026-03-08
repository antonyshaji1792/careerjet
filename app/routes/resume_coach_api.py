"""
Resume Coach API Endpoints
Chat-based resume coaching and feedback
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import logging

from app.services.resume_coach_agent import ResumeCoachAgent, ResumeCoachMode
from app.extensions import db

logger = logging.getLogger(__name__)

# Create blueprint
resume_coach_bp = Blueprint('resume_coach', __name__, url_prefix='/api/resume-coach')


# Rate limiting decorator (simplified)
def rate_limit(max_per_minute=10):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # TODO: Implement proper rate limiting
            return f(*args, **kwargs)
        return wrapped
    return decorator


@resume_coach_bp.route('/chat', methods=['POST'])
@login_required
@rate_limit(max_per_minute=20)
async def chat():
    """
    Chat with resume coach.
    
    Request:
    {
        "message": "How can I improve my resume?",
        "resume_id": 123,
        "job_description": "...",
        "mode": "professional"
    }
    
    Response:
    {
        "response": "Here are some suggestions...",
        "suggestions": [...],
        "intent": "improve",
        "mode": "professional"
    }
    """
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        message = data['message']
        resume_id = data.get('resume_id')
        job_description = data.get('job_description')
        mode = data.get('mode', ResumeCoachMode.PROFESSIONAL)
        
        # Validate mode
        valid_modes = [
            ResumeCoachMode.PROFESSIONAL,
            ResumeCoachMode.FRIENDLY,
            ResumeCoachMode.ROAST,
            ResumeCoachMode.RECRUITER_POV
        ]
        
        if mode not in valid_modes:
            return jsonify({'error': f'Invalid mode. Must be one of: {", ".join(valid_modes)}'}), 400
        
        # Create coach
        coach = ResumeCoachAgent(user_id=current_user.id, mode=mode)
        
        # Get response
        response = await coach.chat(
            message=message,
            resume_id=resume_id,
            job_description=job_description
        )
        
        # Check if blocked
        if response.get('blocked'):
            return jsonify(response), 400
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Chat endpoint failed: {str(e)}")
        return jsonify({'error': 'Failed to process chat message'}), 500


@resume_coach_bp.route('/review/<int:resume_id>', methods=['POST'])
@login_required
@rate_limit(max_per_minute=5)
async def review_resume(resume_id):
    """
    Get comprehensive resume review.
    
    Request:
    {
        "job_description": "...",
        "mode": "professional"
    }
    
    Response:
    {
        "overall_feedback": "...",
        "ats_score": 75,
        "grade": "C",
        "strengths": [...],
        "weaknesses": [...],
        "action_items": [...]
    }
    """
    try:
        data = request.get_json() or {}
        
        job_description = data.get('job_description')
        mode = data.get('mode', ResumeCoachMode.PROFESSIONAL)
        
        # Create coach
        coach = ResumeCoachAgent(user_id=current_user.id, mode=mode)
        
        # Get review
        review = await coach.review_resume(
            resume_id=resume_id,
            job_description=job_description
        )
        
        return jsonify(review), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Review endpoint failed: {str(e)}")
        return jsonify({'error': 'Failed to review resume'}), 500


@resume_coach_bp.route('/analyze-failures/<int:resume_id>', methods=['POST'])
@login_required
@rate_limit(max_per_minute=5)
async def analyze_failures(resume_id):
    """
    Analyze why resume is getting rejected.
    
    Request:
    {
        "job_ids": [1, 2, 3, 4, 5]
    }
    
    Response:
    {
        "analysis": {...},
        "explanation": "...",
        "recommendations": [...]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'job_ids' not in data:
            return jsonify({'error': 'job_ids is required'}), 400
        
        job_ids = data['job_ids']
        
        if not isinstance(job_ids, list) or len(job_ids) == 0:
            return jsonify({'error': 'job_ids must be a non-empty list'}), 400
        
        # Create coach
        coach = ResumeCoachAgent(user_id=current_user.id)
        
        # Analyze
        analysis = await coach.analyze_shortlisting_failure(
            resume_id=resume_id,
            job_ids=job_ids
        )
        
        return jsonify(analysis), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Failure analysis endpoint failed: {str(e)}")
        return jsonify({'error': 'Failed to analyze failures'}), 500


@resume_coach_bp.route('/suggestions/<int:resume_id>', methods=['POST'])
@login_required
@rate_limit(max_per_minute=10)
async def get_suggestions(resume_id):
    """
    Get improvement suggestions.
    
    Request:
    {
        "focus_area": "summary"
    }
    
    Response:
    {
        "focus_area": "summary",
        "suggestions": [...],
        "priority": "high"
    }
    """
    try:
        data = request.get_json() or {}
        
        focus_area = data.get('focus_area')
        
        # Validate focus area
        valid_areas = ['summary', 'experience', 'skills', 'education', 'overall']
        if focus_area and focus_area not in valid_areas:
            return jsonify({'error': f'Invalid focus_area. Must be one of: {", ".join(valid_areas)}'}), 400
        
        # Create coach
        coach = ResumeCoachAgent(user_id=current_user.id)
        
        # Get suggestions
        suggestions = await coach.get_improvement_suggestions(
            resume_id=resume_id,
            focus_area=focus_area
        )
        
        return jsonify(suggestions), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Suggestions endpoint failed: {str(e)}")
        return jsonify({'error': 'Failed to get suggestions'}), 500


@resume_coach_bp.route('/recommend-edits/<int:resume_id>', methods=['POST'])
@login_required
@rate_limit(max_per_minute=5)
async def recommend_edits(resume_id):
    """
    Recommend specific resume edits based on skill gaps.
    
    Request:
    {
        "job_description": "..."
    }
    
    Response:
    {
        "recommendations": "...",
        "gaps": {...},
        "impact": {...}
    }
    """
    try:
        data = request.get_json()
        if not data or 'job_description' not in data:
            return jsonify({'error': 'job_description is required'}), 400
            
        job_description = data['job_description']
        
        # Create coach
        coach = ResumeCoachAgent(user_id=current_user.id)
        
        # Get recommendations
        recommendations = await coach.recommend_resume_edits(
            resume_id=resume_id,
            job_description=job_description
        )
        
        return jsonify(recommendations), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Recommend edits endpoint failed: {str(e)}")
        return jsonify({'error': 'Failed to recommend edits'}), 500


@resume_coach_bp.route('/modes', methods=['GET'])
@login_required
def get_modes():
    """
    Get available coach modes.
    
    Response:
    {
        "modes": [
            {
                "id": "professional",
                "name": "Professional",
                "description": "..."
            },
            ...
        ]
    }
    """
    modes = [
        {
            'id': ResumeCoachMode.PROFESSIONAL,
            'name': 'Professional',
            'description': 'Expert advice with professional tone',
            'emoji': '👔'
        },
        {
            'id': ResumeCoachMode.FRIENDLY,
            'name': 'Friendly',
            'description': 'Encouraging feedback with emojis',
            'emoji': '😊'
        },
        {
            'id': ResumeCoachMode.ROAST,
            'name': 'Roast Mode',
            'description': 'Brutally honest feedback (tough love)',
            'emoji': '🔥'
        },
        {
            'id': ResumeCoachMode.RECRUITER_POV,
            'name': 'Recruiter POV',
            'description': 'Feedback from recruiter perspective',
            'emoji': '👀'
        }
    ]
    
    return jsonify({'modes': modes}), 200


@resume_coach_bp.route('/greeting', methods=['POST'])
@login_required
def get_greeting():
    """
    Get greeting message for selected mode.
    
    Request:
    {
        "mode": "professional"
    }
    
    Response:
    {
        "greeting": "Hello! I'm your AI Resume Coach...",
        "mode": "professional"
    }
    """
    try:
        data = request.get_json() or {}
        mode = data.get('mode', ResumeCoachMode.PROFESSIONAL)
        
        # Create coach
        coach = ResumeCoachAgent(user_id=current_user.id, mode=mode)
        
        greeting = coach.GREETING_TEMPLATES.get(
            mode,
            coach.GREETING_TEMPLATES[ResumeCoachMode.PROFESSIONAL]
        )
        
        return jsonify({
            'greeting': greeting,
            'mode': mode
        }), 200
        
    except Exception as e:
        logger.error(f"Greeting endpoint failed: {str(e)}")
        return jsonify({'error': 'Failed to get greeting'}), 500


# Error handlers
@resume_coach_bp.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Bad request'}), 400


@resume_coach_bp.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found'}), 404


@resume_coach_bp.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500
