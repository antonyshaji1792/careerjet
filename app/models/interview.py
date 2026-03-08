from datetime import datetime
from app.extensions import db

class AIInterview(db.Model):
    """
    Represents an AI interview session.
    """
    __tablename__ = 'ai_interviews'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    job_title = db.Column(db.String(255), nullable=False)
    company_name = db.Column(db.String(255))
    job_description = db.Column(db.Text)
    difficulty = db.Column(db.String(50), default='medium')
    status = db.Column(db.String(50), default='in_progress')  # in_progress, completed, abandoned
    overall_score = db.Column(db.Float, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    questions = db.relationship('AIInterviewQuestion', backref='interview', lazy=True, cascade="all, delete-orphan")
    summary = db.relationship('AIInterviewSummary', backref='interview', uselist=False, cascade="all, delete-orphan")
    skill_gaps = db.relationship('AIInterviewSkillGap', backref='interview', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'job_title': self.job_title,
            'company_name': self.company_name,
            'status': self.status,
            'overall_score': self.overall_score,
            'created_at': self.created_at.isoformat()
        }

class AIInterviewQuestion(db.Model):
    """
    Individual questions generated for an interview.
    """
    __tablename__ = 'ai_interview_questions'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('ai_interviews.id'), nullable=False, index=True)
    question_text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))  # technical, behavioral, situational
    difficulty = db.Column(db.String(50))
    order_index = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    answer = db.relationship('AIInterviewAnswer', backref='question', uselist=False, cascade="all, delete-orphan")

class AIInterviewAnswer(db.Model):
    """
    User's answer to a specific question and the AI evaluation.
    """
    __tablename__ = 'ai_interview_answers'

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('ai_interview_questions.id'), nullable=False, unique=True)
    user_answer = db.Column(db.Text)
    ai_feedback = db.Column(db.Text)  # General feedback text
    score = db.Column(db.Float)  # 0-100
    strengths_json = db.Column(db.JSON)  # List of strengths
    weaknesses_json = db.Column(db.JSON)  # List of weaknesses
    improved_answer = db.Column(db.Text)  # AI suggested answer
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AIInterviewSkillGap(db.Model):
    """
    Skills identified as missing or weak during the interview.
    """
    __tablename__ = 'ai_interview_skill_gaps'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('ai_interviews.id'), nullable=False, index=True)
    skill_name = db.Column(db.String(100), nullable=False)
    gap_type = db.Column(db.String(50))  # missing, weak
    suggested_action = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AIInterviewSummary(db.Model):
    """
    Final summary and report card for the interview session.
    """
    __tablename__ = 'ai_interview_summaries'

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('ai_interviews.id'), nullable=False, unique=True)
    summary_text = db.Column(db.Text)
    key_strengths_json = db.Column(db.JSON)
    key_areas_improvement_json = db.Column(db.JSON)
    recommended_resources_json = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
