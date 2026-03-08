from datetime import datetime
from app.extensions import db

class ProfileHeadline(db.Model):
    """User's professional headline"""
    __tablename__ = 'profile_headline'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    headline = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class KeySkill(db.Model):
    """Individual skills"""
    __tablename__ = 'key_skills'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Employment(db.Model):
    """Employment history"""
    __tablename__ = 'employment'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    employment_type = db.Column(db.String(50))  # Full-time, Part-time, Contract, etc.
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)  # Null if current job
    is_current = db.Column(db.Boolean, default=False)
    is_serving_notice = db.Column(db.Boolean, default=False)
    notice_period_days = db.Column(db.Integer)
    description = db.Column(db.Text)
    key_skills = db.Column(db.Text)  # Comma-separated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Education(db.Model):
    """Education history"""
    __tablename__ = 'education'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    degree = db.Column(db.String(200), nullable=False)
    institution = db.Column(db.String(200), nullable=False)
    field_of_study = db.Column(db.String(200))
    start_year = db.Column(db.Integer)
    end_year = db.Column(db.Integer)
    grade = db.Column(db.String(50))
    education_type = db.Column(db.String(50))  # Full Time, Part Time, Distance Learning
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ITSkill(db.Model):
    """IT/Technical skills with proficiency"""
    __tablename__ = 'it_skills'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    version = db.Column(db.String(50))
    last_used_year = db.Column(db.Integer)
    experience_years = db.Column(db.Integer)
    experience_months = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Project(db.Model):
    """Projects portfolio"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    client = db.Column(db.String(200))
    project_status = db.Column(db.String(50))  # In Progress, Finished
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    description = db.Column(db.Text)
    role = db.Column(db.String(200))
    team_size = db.Column(db.Integer)
    skills_used = db.Column(db.Text)  # Comma-separated
    project_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProfileSummary(db.Model):
    """Professional summary"""
    __tablename__ = 'profile_summary'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Accomplishment(db.Model):
    """Accomplishments - certifications, awards, publications, etc."""
    __tablename__ = 'accomplishments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # online_profile, work_sample, certification, publication, patent
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(500))
    description = db.Column(db.Text)
    issued_by = db.Column(db.String(200))
    issued_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PersonalDetails(db.Model):
    """Personal information"""
    __tablename__ = 'personal_details'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(200))
    gender = db.Column(db.String(20))
    marital_status = db.Column(db.String(50))
    date_of_birth = db.Column(db.Date)
    category = db.Column(db.String(50))  # General, SC, ST, OBC, etc.
    work_permit_country = db.Column(db.String(100))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    phone = db.Column(db.String(20))
    alternate_phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Language(db.Model):
    """Languages known"""
    __tablename__ = 'languages'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    language_name = db.Column(db.String(100), nullable=False)
    proficiency = db.Column(db.String(50))  # Beginner, Intermediate, Proficient, Expert
    can_read = db.Column(db.Boolean, default=False)
    can_write = db.Column(db.Boolean, default=False)
    can_speak = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DiversityInfo(db.Model):
    """Diversity and inclusion information"""
    __tablename__ = 'diversity_info'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    has_disability = db.Column(db.Boolean, default=False)
    disability_type = db.Column(db.String(200))
    has_military_experience = db.Column(db.Boolean, default=False)
    military_branch = db.Column(db.String(100))
    military_start_date = db.Column(db.Date)
    military_end_date = db.Column(db.Date)
    has_career_break = db.Column(db.Boolean, default=False)
    career_break_reason = db.Column(db.String(200))
    career_break_start_date = db.Column(db.Date)
    career_break_end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CareerProfile(db.Model):
    """Career preferences and goals"""
    __tablename__ = 'career_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    current_industry = db.Column(db.String(200))
    preferred_industries = db.Column(db.Text)  # Comma-separated
    current_salary = db.Column(db.Integer)
    expected_salary = db.Column(db.Integer)
    preferred_shift = db.Column(db.String(50))  # Day, Night, Flexible
    preferred_employment_type = db.Column(db.String(100))  # Full-time, Part-time, Contract
    willing_to_relocate = db.Column(db.Boolean, default=False)
    preferred_work_location = db.Column(db.Text)  # Comma-separated cities
    notice_period_days = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
