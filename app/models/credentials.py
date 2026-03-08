from datetime import datetime
from app.extensions import db

class LinkedInCredentials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_encrypted = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    session_cookies = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        from cryptography.fernet import Fernet
        import os
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if not key: raise ValueError("LINKEDIN_ENCRYPTION_KEY not set")
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        self.password_encrypted = cipher.encrypt(password.encode()).decode()

    def get_password(self):
        from cryptography.fernet import Fernet
        import os
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if not key: raise ValueError("Encryption key not found")
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        return cipher.decrypt(self.password_encrypted.encode()).decode()

class NaukriCredentials(db.Model):
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
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if not key: raise ValueError("Encryption key not set")
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        self.password_encrypted = cipher.encrypt(password.encode()).decode()
    
    def get_password(self):
        from cryptography.fernet import Fernet
        import os
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if not key: raise ValueError("Encryption key not set")
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        return cipher.decrypt(self.password_encrypted.encode()).decode()

class PlatformCredential(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    platform = db.Column(db.String(50), nullable=False)
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
        if not key: raise ValueError("Encryption key not set")
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        self.password_encrypted = cipher.encrypt(password.encode()).decode()

    def get_password(self):
        from cryptography.fernet import Fernet
        import os
        key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
        if not key: raise ValueError("Encryption key not set")
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        return cipher.decrypt(self.password_encrypted.encode()).decode()
