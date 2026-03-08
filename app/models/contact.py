from app.extensions import db
from datetime import datetime

class ContactThread(db.Model):
    __tablename__ = 'contact_threads'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Null for guest
    guest_name = db.Column(db.String(100), nullable=True)
    guest_email = db.Column(db.String(120), nullable=True)
    subject = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='open') # open, replied, closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('contact_threads', lazy=True))
    messages = db.relationship('ContactMessage', backref='thread', lazy=True, cascade="all, delete-orphan", order_by="ContactMessage.created_at")

    @property
    def display_name(self):
        if self.user:
            return self.user.email
        return self.guest_name or self.guest_email

    @property
    def last_message(self):
        return self.messages[-1] if self.messages else None

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('contact_threads.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sender = db.relationship('User', backref=db.backref('sent_contact_messages', lazy=True))
