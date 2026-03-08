from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skills = db.Column(db.Text)  # Comma-separated or JSON
    experience = db.Column(db.Integer)  # Years
    preferred_roles = db.Column(db.Text)
    preferred_locations = db.Column(db.Text)

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_path = db.Column(db.String(255)) # Optional for AI generated
    content_json = db.Column(db.Text) # Stored JSON of resume sections
    is_primary = db.Column(db.Boolean, default=False)
    is_generated = db.Column(db.Boolean, default=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    optimizations = db.relationship('ResumeOptimization', backref='resume', lazy=True)

class ResumeOptimization(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resume.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id'))
    optimized_content = db.Column(db.Text) # JSON
    ats_score = db.Column(db.Integer)
    missing_keywords = db.Column(db.Text)
    suggestions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CoverLetter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class JobPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200))
    platform = db.Column(db.String(50))
    job_url = db.Column(db.String(500), unique=True, nullable=False)
    description = db.Column(db.Text)
    posted_at = db.Column(db.DateTime)
    ingested_at = db.Column(db.DateTime, default=datetime.utcnow)

class JobMatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id'), nullable=False)
    match_score = db.Column(db.Float)
    is_applied = db.Column(db.Boolean, default=False)
    is_scheduled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    job = db.relationship('JobPost', backref='matches')

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_post.id'), nullable=False)
    status = db.Column(db.String(50), default='Scheduled')  # Scheduled, Applied, Failed, Skipped
    applied_at = db.Column(db.DateTime)
    status_message = db.Column(db.String(255)) # Real-time progress
    error_message = db.Column(db.Text)
    screenshot_path = db.Column(db.String(255)) # Path to failure screenshot

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    daily_limit = db.Column(db.Integer, default=5)
    daily_search_limit = db.Column(db.Integer, default=20)
    is_autopilot_enabled = db.Column(db.Boolean, default=False)
    preferred_days = db.Column(db.String(100))  # e.g., "Monday,Tuesday,Wednesday"
    preferred_time = db.Column(db.String(50))  # e.g., "09:00-17:00"
    match_threshold = db.Column(db.Integer, default=70) # Minimum match score (0-100)
    last_run_at = db.Column(db.DateTime)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    plan = db.Column(db.String(50), default='Free')
    status = db.Column(db.String(50), default='Active')
    stripe_subscription_id = db.Column(db.String(100))

class WebsitePreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform_name = db.Column(db.String(100), nullable=False)  # e.g., "LinkedIn", "Indeed", "Naukri"
    is_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LinkedInCredentials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_encrypted = db.Column(db.Text, nullable=False)  # Encrypted password
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    session_cookies = db.Column(db.Text)  # Store session for reuse
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        """Encrypt and store LinkedIn password"""
        from cryptography.fernet import Fernet
        import os
        
        # Get encryption key from environment
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if not key:
            # Fallback for development if not in .env (though we just added it)
            # In production this should always be set
            raise ValueError("LINKEDIN_ENCRYPTION_KEY environment variable is not set. Please add it to your .env file.")
        
        try:
            cipher = Fernet(key.encode() if isinstance(key, str) else key)
            self.password_encrypted = cipher.encrypt(password.encode()).decode()
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")
    
    def get_password(self):
        """Decrypt and return LinkedIn password"""
        from cryptography.fernet import Fernet
        import os
        
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if not key:
            raise ValueError("Encryption key not found. Please ensure LINKEDIN_ENCRYPTION_KEY is set in your .env file.")
        
        try:
            cipher = Fernet(key.encode() if isinstance(key, str) else key)
            return cipher.decrypt(self.password_encrypted.encode()).decode()
        except Exception as e:
            # This happens if the key changed or is invalid
            raise ValueError("Could not decrypt password. The encryption key may have changed. Please re-enter your LinkedIn credentials.")

class LinkedInJob(db.Model):
    """Cache for LinkedIn job postings"""
    id = db.Column(db.Integer, primary_key=True)
    linkedin_job_id = db.Column(db.String(255), unique=True, nullable=False)  # LinkedIn's job ID
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    description = db.Column(db.Text)
    job_url = db.Column(db.String(500), nullable=False)
    is_easy_apply = db.Column(db.Boolean, default=False)
    salary_range = db.Column(db.String(100))
    employment_type = db.Column(db.String(50))  # Full-time, Part-time, Contract, etc.
    seniority_level = db.Column(db.String(50))  # Entry, Mid, Senior, etc.
    posted_at = db.Column(db.DateTime)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class NaukriCredentials(db.Model):
    """Secure storage for Naukri.com account access"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_encrypted = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        from cryptography.fernet import Fernet
        import os
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY') # Reusing same key for simplicity
        if not key:
            raise ValueError("Encryption key not set")
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        self.password_encrypted = cipher.encrypt(password.encode()).decode()
    
    def get_password(self):
        from cryptography.fernet import Fernet
        import os
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if not key:
            raise ValueError("Encryption key not set")
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        return cipher.decrypt(self.password_encrypted.encode()).decode()

class NaukriJob(db.Model):
    """Cache for Naukri.com job postings"""
    id = db.Column(db.Integer, primary_key=True)
    naukri_job_id = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    experience_required = db.Column(db.String(100))
    salary_range = db.Column(db.String(100))
    job_url = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    skills_required = db.Column(db.Text)
    posted_at = db.Column(db.String(100)) # Naukri often shows "Just now", "2 days ago"
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class JobAlert(db.Model):
    """User job alert configurations"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Alert name (e.g., "Senior Python Jobs")
    keywords = db.Column(db.Text, nullable=False)  # Comma-separated keywords
    location = db.Column(db.String(255))  # Location filter
    platforms = db.Column(db.Text)  # Comma-separated platforms (LinkedIn, Indeed, etc.)
    frequency = db.Column(db.String(50), default='instant')  # instant, daily, weekly
    is_active = db.Column(db.Boolean, default=True)
    last_checked = db.Column(db.DateTime, default=datetime.utcnow)
    email_enabled = db.Column(db.Boolean, default=True)
    sms_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SystemConfig(db.Model):
    """Global system configuration settings (API keys, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    is_encrypted = db.Column(db.Boolean, default=False)
    description = db.Column(db.String(255))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @staticmethod
    def get_config_value(key, default=None):
        config = SystemConfig.query.filter_by(key=key).first()
        if not config or not config.value:
            return default
        if config.is_encrypted:
            try:
                from cryptography.fernet import Fernet
                import os
                enc_key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
                if not enc_key:
                    return config.value
                cipher = Fernet(enc_key.encode() if isinstance(enc_key, str) else enc_key)
                return cipher.decrypt(config.value.encode()).decode()
            except Exception:
                return default
        return config.value

    @staticmethod
    def set_config_value(key, value, is_encrypted=False, description=None):
        config = SystemConfig.query.filter_by(key=key).first()
        if not config:
            config = SystemConfig(key=key)
        
        config.is_encrypted = is_encrypted
        if description:
            config.description = description
        
        if is_encrypted and value:
            from cryptography.fernet import Fernet
            import os
            enc_key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
            if not enc_key:
                raise ValueError("LINKEDIN_ENCRYPTION_KEY not set for encryption")
            cipher = Fernet(enc_key.encode() if isinstance(enc_key, str) else enc_key)
            config.value = cipher.encrypt(value.encode()).decode()
        else:
            config.value = value
            
        db.session.add(config)
        db.session.commit()
class PlatformCredential(db.Model):
    """Universal storage for various job platform credentials"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # Indeed, Monster, Glassdoor, etc.
    email = db.Column(db.String(255), nullable=False)
    password_encrypted = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        from cryptography.fernet import Fernet
        import os
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if not key:
            raise ValueError("Encryption key not set")
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        self.password_encrypted = cipher.encrypt(password.encode()).decode()

    def get_password(self):
        from cryptography.fernet import Fernet
        import os
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if not key:
            raise ValueError("Encryption key not set")
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        return cipher.decrypt(self.password_encrypted.encode()).decode()

class AnswerCache(db.Model):
    """Cache for AI-generated answers to common job application questions"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.Index('idx_user_question', 'user_id', 'question_text'),)
