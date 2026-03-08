from datetime import datetime
from app.extensions import db

class AIVideoInterview(db.Model):
    """
    Represents an AI Video Interview session with avatar interaction.
    """
    __tablename__ = 'ai_video_interviews'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Session Configuration
    job_title = db.Column(db.String(255), nullable=False)
    company_name = db.Column(db.String(255))
    difficulty = db.Column(db.String(50), default='medium')
    
    # Video/Avatar specific
    camera_enabled = db.Column(db.Boolean, default=False)
    persona_id = db.Column(db.String(50)) # e.g. 'professional_recruiter'
    avatar_id = db.Column(db.String(50)) # e.g. 'avatar_01'
    
    # Session Metadata
    status = db.Column(db.String(50), default='in_progress')
    duration_seconds = db.Column(db.Integer, default=0)
    overall_score = db.Column(db.Float, nullable=True)
    video_url = db.Column(db.String(500))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    questions = db.relationship('AIVideoQuestion', backref='video_interview', lazy=True, cascade="all, delete-orphan")
    summary = db.relationship('AIVideoSummary', backref='video_interview', uselist=False, cascade="all, delete-orphan")

class AIVideoQuestion(db.Model):
    """
    Questions asked during the video interview.
    """
    __tablename__ = 'ai_video_questions'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('ai_video_interviews.id'), nullable=False, index=True)
    
    question_text = db.Column(db.Text, nullable=False)
    order_index = db.Column(db.Integer, default=0)
    category = db.Column(db.String(100))
    
    # Relationships
    answer = db.relationship('AIVideoAnswer', backref='question', uselist=False, cascade="all, delete-orphan")

class AIVideoAnswer(db.Model):
    """
    User's spoken response (transcribed).
    """
    __tablename__ = 'ai_video_answers'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('ai_video_questions.id'), nullable=False, unique=True)
    
    # Transcript & Audio
    audio_transcript = db.Column(db.Text) # The STT result
    audio_url = db.Column(db.String(500)) # Optional: path to stored audio file
    
    # Speech Metrics
    confidence_score = db.Column(db.Float) # STT confidence or AI confidence in answer
    speaking_pace_wpm = db.Column(db.Integer) # Words per minute
    silent_pauses_count = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    evaluation = db.relationship('AIVideoEvaluation', backref='answer', uselist=False, cascade="all, delete-orphan")

class AIVideoEvaluation(db.Model):
    """
    AI assessment of the video/audio answer.
    """
    __tablename__ = 'ai_video_evaluations'

    id = db.Column(db.Integer, primary_key=True)
    answer_id = db.Column(db.Integer, db.ForeignKey('ai_video_answers.id'), nullable=False, unique=True)
    
    score = db.Column(db.Float) # 0-100
    feedback_text = db.Column(db.Text)
    
    # Dimensional Scores
    clarity_score = db.Column(db.Float) # How clear was the communication
    relevance_score = db.Column(db.Float) # Did they answer the question
    completeness_score = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AIVideoSummary(db.Model):
    """
    Final report for video interview.
    """
    __tablename__ = 'ai_video_summaries'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('ai_video_interviews.id'), nullable=False, unique=True)
    
    summary_text = db.Column(db.Text)
    
    # Aggregated Metrics
    average_pace_wpm = db.Column(db.Float)
    average_confidence = db.Column(db.Float)
    
    key_strengths_json = db.Column(db.JSON)
    areas_for_improvement_json = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
