from datetime import datetime
from app.extensions import db

class SystemConfig(db.Model):
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
                if not enc_key: return config.value
                cipher = Fernet(enc_key.encode() if isinstance(enc_key, str) else enc_key)
                return cipher.decrypt(config.value.encode()).decode()
            except Exception:
                return default
        return config.value

    @staticmethod
    def set_config_value(key, value, is_encrypted=False, description=None):
        config = SystemConfig.query.filter_by(key=key).first()
        if not config: config = SystemConfig(key=key)
        config.is_encrypted = is_encrypted
        if description: config.description = description
        if is_encrypted and value:
            from cryptography.fernet import Fernet
            import os
            enc_key = os.environ.get('LINKEDIN_ENCRYPTION_KEY')
            if not enc_key: raise ValueError("LINKEDIN_ENCRYPTION_KEY not set")
            cipher = Fernet(enc_key.encode() if isinstance(enc_key, str) else enc_key)
            config.value = cipher.encrypt(value.encode()).decode()
        else:
            config.value = value
        db.session.add(config)
        db.session.commit()

class AnswerCache(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.Index('idx_user_question', 'user_id', 'question_text'),)

class CoverLetter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
