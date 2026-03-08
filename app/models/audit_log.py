from datetime import datetime
from app.extensions import db

class AuditLog(db.Model):
    """
    Immutable audit log for enterprise compliance and security tracking.
    Records all critical actions for regulatory compliance.
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # e.g., 'bulk_upload', 'compliance_export'
    details = db.Column(db.Text)  # JSON string with action details
    ip_address = db.Column(db.String(45))  # IPv4 or IPv6
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Immutability: No update or delete methods
    # Once created, audit logs cannot be modified
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat()
        }
