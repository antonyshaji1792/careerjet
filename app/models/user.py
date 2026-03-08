from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_super_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    profile = db.relationship('UserProfile', backref='user', uselist=False)
    resumes = db.relationship('Resume', backref='user', lazy=True)
    cover_letters = db.relationship('CoverLetter', backref='user', lazy=True)
    job_matches = db.relationship('JobMatch', backref='user', lazy=True)
    applications = db.relationship('Application', backref='user', lazy=True)
    schedule = db.relationship('Schedule', backref='user', uselist=False)
    subscription = db.relationship('Subscription', backref='user', uselist=False)
    website_preferences = db.relationship('WebsitePreference', backref='user', lazy=True)
    linkedin_credentials = db.relationship('LinkedInCredentials', backref='user', uselist=False)
    naukri_credentials = db.relationship('NaukriCredentials', backref='user', uselist=False)
    platform_credentials = db.relationship('PlatformCredential', backref='user', lazy=True)
    job_alerts = db.relationship('JobAlert', backref='user', lazy=True)
    
    # Profile relationships
    headline = db.relationship('ProfileHeadline', backref='user', uselist=False, lazy=True)
    key_skills = db.relationship('KeySkill', backref='user', lazy=True)
    employments = db.relationship('Employment', backref='user', lazy=True, order_by='Employment.start_date.desc()')
    educations = db.relationship('Education', backref='user', lazy=True, order_by='Education.end_year.desc()')
    it_skills = db.relationship('ITSkill', backref='user', lazy=True)
    projects = db.relationship('Project', backref='user', lazy=True, order_by='Project.start_date.desc()')
    summary = db.relationship('ProfileSummary', backref='user', uselist=False, lazy=True)
    accomplishments = db.relationship('Accomplishment', backref='user', lazy=True)
    personal_details = db.relationship('PersonalDetails', backref='user', uselist=False, lazy=True)
    languages = db.relationship('Language', backref='user', lazy=True)
    diversity_info = db.relationship('DiversityInfo', backref='user', uselist=False, lazy=True)
    career_profile = db.relationship('CareerProfile', backref='user', uselist=False, lazy=True)

    @property
    def current_job(self):
        """Returns the current employment record."""
        return next((e for e in self.employments if e.is_current), None)

    @property
    def total_experience(self):
        """Returns total experience in years."""
        if hasattr(self, 'profile') and self.profile and self.profile.experience is not None:
            try:
                # return as rounded float with one decimal when possible
                return round(float(self.profile.experience), 1)
            except (ValueError, TypeError):
                return 0
        return 0

    @property
    def current_location(self):
        """Returns a formatted string of the user's city and country."""
        if hasattr(self, 'personal_details') and self.personal_details:
             parts = []
             if self.personal_details.city: parts.append(self.personal_details.city)
             if self.personal_details.country: parts.append(self.personal_details.country)
             return ", ".join(parts)
        return ""

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skills = db.Column(db.Text)
    experience = db.Column(db.Float)
    preferred_roles = db.Column(db.Text)
    preferred_locations = db.Column(db.Text)
    profile_picture_path = db.Column(db.String(255))

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    daily_limit = db.Column(db.Integer, default=5)
    daily_search_limit = db.Column(db.Integer, default=20)
    is_autopilot_enabled = db.Column(db.Boolean, default=False)
    preferred_days = db.Column(db.String(100))
    preferred_time = db.Column(db.String(50))
    match_threshold = db.Column(db.Integer, default=70)
    last_run_at = db.Column(db.DateTime)


class WebsitePreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform_name = db.Column(db.String(100), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
