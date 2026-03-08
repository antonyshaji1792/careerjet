"""
Skill Gap Intelligence Database Models
Comprehensive skill tracking, analysis, and market intelligence
"""

from app.extensions import db
from datetime import datetime
from sqlalchemy import Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB


class SkillCategory:
    """Skill category constants"""
    HARD_SKILL = 'hard_skill'
    SOFT_SKILL = 'soft_skill'
    TOOL = 'tool'
    FRAMEWORK = 'framework'
    LANGUAGE = 'language'
    PLATFORM = 'platform'
    METHODOLOGY = 'methodology'


class SkillSource:
    """Skill source constants"""
    RESUME = 'resume'
    JOB = 'job'
    INFERRED = 'inferred'
    USER_INPUT = 'user_input'
    AI_EXTRACTED = 'ai_extracted'


class ProficiencyLevel:
    """Proficiency level constants"""
    BEGINNER = 'beginner'
    INTERMEDIATE = 'intermediate'
    ADVANCED = 'advanced'
    EXPERT = 'expert'
    UNKNOWN = 'unknown'


class ResumeSkillExtracted(db.Model):
    """
    Skills extracted from resumes with metadata.
    Normalized and categorized for intelligent matching.
    """
    __tablename__ = 'resume_skills_extracted'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    
    # Skill information
    skill_name = db.Column(db.String(100), nullable=False, index=True)
    skill_name_normalized = db.Column(db.String(100), nullable=False, index=True)  # lowercase, trimmed
    category = db.Column(db.String(50), nullable=False, index=True)  # SkillCategory
    
    # Proficiency and context
    proficiency_level = db.Column(db.String(20), default=ProficiencyLevel.UNKNOWN)
    years_of_experience = db.Column(db.Float, nullable=True)  # Extracted or inferred
    context = db.Column(db.Text, nullable=True)  # Where skill was mentioned
    
    # Scoring
    ats_weight = db.Column(db.Float, default=1.0)  # ATS importance weight
    confidence_score = db.Column(db.Float, default=1.0)  # Extraction confidence (0-1)
    
    # Source tracking
    source = db.Column(db.String(20), nullable=False, default=SkillSource.AI_EXTRACTED)
    extraction_method = db.Column(db.String(50), nullable=True)  # e.g., 'regex', 'nlp', 'manual'
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resume = db.relationship('Resume', backref=db.backref('extracted_skills', lazy='dynamic', cascade='all, delete-orphan'))
    user = db.relationship('User', backref=db.backref('resume_skills', lazy='dynamic'))
    
    # Constraints
    __table_args__ = (
        Index('idx_resume_skill_lookup', 'resume_id', 'skill_name_normalized'),
        Index('idx_user_skills', 'user_id', 'skill_name_normalized'),
        Index('idx_category_proficiency', 'category', 'proficiency_level'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='check_confidence_range'),
        CheckConstraint('ats_weight >= 0', name='check_ats_weight_positive'),
    )
    
    def __repr__(self):
        return f'<ResumeSkill {self.skill_name} ({self.category})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'skill_name': self.skill_name,
            'category': self.category,
            'proficiency_level': self.proficiency_level,
            'years_of_experience': self.years_of_experience,
            'ats_weight': self.ats_weight,
            'confidence_score': self.confidence_score,
            'source': self.source
        }


class JobSkillExtracted(db.Model):
    """
    Skills extracted from job descriptions with requirement metadata.
    Tracks market demand and skill importance.
    """
    __tablename__ = 'job_skills_extracted'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id', ondelete='CASCADE'), nullable=False)
    
    # Skill information
    skill_name = db.Column(db.String(100), nullable=False, index=True)
    skill_name_normalized = db.Column(db.String(100), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    
    # Requirement level
    requirement_type = db.Column(db.String(20), nullable=False, index=True)  # mandatory, preferred, nice_to_have
    priority_score = db.Column(db.Float, default=5.0)  # 1-10 scale
    
    # Market intelligence
    market_demand_score = db.Column(db.Float, default=5.0)  # 1-10 based on frequency across jobs
    salary_impact = db.Column(db.Float, nullable=True)  # Estimated salary impact percentage
    
    # Context
    context = db.Column(db.Text, nullable=True)  # Sentence where skill was mentioned
    section = db.Column(db.String(50), nullable=True)  # requirements, responsibilities, etc.
    
    # Scoring
    ats_weight = db.Column(db.Float, default=1.0)
    confidence_score = db.Column(db.Float, default=1.0)
    
    # Source tracking
    source = db.Column(db.String(20), nullable=False, default=SkillSource.AI_EXTRACTED)
    extraction_method = db.Column(db.String(50), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = db.relationship('JobPost', backref=db.backref('extracted_skills', lazy='dynamic', cascade='all, delete-orphan'))
    
    # Constraints
    __table_args__ = (
        Index('idx_job_skill_lookup', 'job_id', 'skill_name_normalized'),
        Index('idx_skill_requirement', 'skill_name_normalized', 'requirement_type'),
        Index('idx_market_demand', 'market_demand_score', 'category'),
        CheckConstraint('confidence_score >= 0 AND confidence_score <= 1', name='check_job_confidence_range'),
        CheckConstraint('priority_score >= 1 AND priority_score <= 10', name='check_priority_range'),
        CheckConstraint('market_demand_score >= 1 AND market_demand_score <= 10', name='check_demand_range'),
    )
    
    def __repr__(self):
        return f'<JobSkill {self.skill_name} ({self.requirement_type})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'skill_name': self.skill_name,
            'category': self.category,
            'requirement_type': self.requirement_type,
            'priority_score': self.priority_score,
            'market_demand_score': self.market_demand_score,
            'ats_weight': self.ats_weight,
            'confidence_score': self.confidence_score
        }


class SkillGapAnalysis(db.Model):
    """
    Stores skill gap analysis results for resume-job pairs.
    Enables tracking of progress and historical comparisons.
    """
    __tablename__ = 'skill_gap_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id', ondelete='CASCADE'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id', ondelete='SET NULL'), nullable=True)
    
    # Analysis results
    match_percentage = db.Column(db.Float, nullable=False)
    ats_score = db.Column(db.Float, nullable=True)
    potential_score = db.Column(db.Float, nullable=True)
    
    # Gap counts
    total_jd_skills = db.Column(db.Integer, default=0)
    total_resume_skills = db.Column(db.Integer, default=0)
    mandatory_missing = db.Column(db.Integer, default=0)
    preferred_missing = db.Column(db.Integer, default=0)
    nice_to_have_missing = db.Column(db.Integer, default=0)
    matched_skills_count = db.Column(db.Integer, default=0)
    
    # Detailed results (JSON)
    skill_gaps = db.Column(db.JSON, nullable=True)  # {mandatory: [], preferred: [], nice_to_have: []}
    matched_skills = db.Column(db.JSON, nullable=True)  # List of matched skills
    ranked_gaps = db.Column(db.JSON, nullable=True)  # Ranked by ATS impact
    learning_paths = db.Column(db.JSON, nullable=True)  # Suggested learning paths
    score_predictions = db.Column(db.JSON, nullable=True)  # Score improvement predictions
    category_breakdown = db.Column(db.JSON, nullable=True)  # Analysis by category
    recommendations = db.Column(db.JSON, nullable=True)  # Actionable recommendations
    
    # Market context
    market_insights = db.Column(db.JSON, nullable=True)  # Market demand data
    
    # Metadata
    analysis_version = db.Column(db.String(20), default='2.0')  # Track algorithm version
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('skill_gap_analyses', lazy='dynamic'))
    resume = db.relationship('Resume', backref=db.backref('skill_gap_analyses', lazy='dynamic'))
    job = db.relationship('JobPost', backref=db.backref('skill_gap_analyses', lazy='dynamic'))
    
    # Constraints
    __table_args__ = (
        Index('idx_user_analysis', 'user_id', 'created_at'),
        Index('idx_resume_job_analysis', 'resume_id', 'job_id'),
        Index('idx_match_score', 'match_percentage', 'ats_score'),
        CheckConstraint('match_percentage >= 0 AND match_percentage <= 100', name='check_match_percentage'),
    )
    
    def __repr__(self):
        return f'<SkillGapAnalysis resume={self.resume_id} job={self.job_id} match={self.match_percentage}%>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'match_percentage': self.match_percentage,
            'ats_score': self.ats_score,
            'potential_score': self.potential_score,
            'mandatory_missing': self.mandatory_missing,
            'preferred_missing': self.preferred_missing,
            'skill_gaps': self.skill_gaps,
            'matched_skills': self.matched_skills,
            'recommendations': self.recommendations,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SkillImpactScore(db.Model):
    """
    Global skill impact scores based on market analysis.
    Updated periodically from job market data.
    """
    __tablename__ = 'skill_impact_scores'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Skill information
    skill_name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    skill_name_normalized = db.Column(db.String(100), nullable=False, unique=True, index=True)
    category = db.Column(db.String(50), nullable=False, index=True)
    
    # Impact scores
    ats_weight = db.Column(db.Float, default=1.0)  # Default ATS weight
    market_demand_score = db.Column(db.Float, default=5.0)  # 1-10 scale
    salary_impact_percentage = db.Column(db.Float, nullable=True)  # Average salary impact
    
    # Market statistics
    job_frequency = db.Column(db.Integer, default=0)  # Times seen in job postings
    mandatory_frequency = db.Column(db.Integer, default=0)  # Times listed as mandatory
    preferred_frequency = db.Column(db.Integer, default=0)  # Times listed as preferred
    
    # Trend data
    trend_score = db.Column(db.Float, default=0.0)  # Positive = growing, negative = declining
    growth_rate = db.Column(db.Float, nullable=True)  # Percentage growth over time
    
    # Related skills (JSON array)
    related_skills = db.Column(db.JSON, nullable=True)  # Often appears with these skills
    alternative_names = db.Column(db.JSON, nullable=True)  # Synonyms and variations
    
    # Learning metadata
    avg_learning_time_weeks = db.Column(db.Integer, nullable=True)
    difficulty_level = db.Column(db.String(20), default='intermediate')
    
    # Metadata
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    data_points = db.Column(db.Integer, default=0)  # Number of jobs analyzed
    
    # Constraints
    __table_args__ = (
        Index('idx_demand_category', 'market_demand_score', 'category'),
        Index('idx_trending', 'trend_score', 'market_demand_score'),
        CheckConstraint('market_demand_score >= 1 AND market_demand_score <= 10', name='check_impact_demand_range'),
        CheckConstraint('ats_weight >= 0', name='check_impact_ats_weight'),
    )
    
    def __repr__(self):
        return f'<SkillImpact {self.skill_name} demand={self.market_demand_score}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'skill_name': self.skill_name,
            'category': self.category,
            'ats_weight': self.ats_weight,
            'market_demand_score': self.market_demand_score,
            'salary_impact_percentage': self.salary_impact_percentage,
            'job_frequency': self.job_frequency,
            'trend_score': self.trend_score,
            'related_skills': self.related_skills,
            'difficulty_level': self.difficulty_level
        }
    
    @classmethod
    def get_or_create(cls, skill_name: str, category: str = SkillCategory.HARD_SKILL):
        """Get existing or create new skill impact score"""
        normalized = skill_name.lower().strip()
        skill = cls.query.filter_by(skill_name_normalized=normalized).first()
        
        if not skill:
            skill = cls(
                skill_name=skill_name,
                skill_name_normalized=normalized,
                category=category
            )
            db.session.add(skill)
            db.session.flush()
        
        return skill
    
    @classmethod
    def update_from_jobs(cls, skill_name: str, requirement_type: str):
        """Update skill impact from job data"""
        skill = cls.get_or_create(skill_name)
        
        skill.job_frequency += 1
        
        if requirement_type == 'mandatory':
            skill.mandatory_frequency += 1
            skill.ats_weight = max(skill.ats_weight, 10.0)
        elif requirement_type == 'preferred':
            skill.preferred_frequency += 1
            skill.ats_weight = max(skill.ats_weight, 5.0)
        
        # Recalculate market demand
        total = skill.mandatory_frequency + skill.preferred_frequency
        if total > 0:
            demand = (skill.mandatory_frequency * 10 + skill.preferred_frequency * 5) / total
            skill.market_demand_score = min(10.0, demand)
        
        skill.last_updated = datetime.utcnow()
        skill.data_points += 1
        
        return skill
