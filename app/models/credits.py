from datetime import datetime
from app.extensions import db

class CreditWallet(db.Model):
    """
    Users current credit balance.
    """
    __tablename__ = 'credit_wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    balance_credits = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('credit_wallet', uselist=False))

class CreditTransaction(db.Model):
    """
    Ledger for all credit events.
    """
    __tablename__ = 'credit_transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False) # subscription, usage, topup, admin_adjustment
    credits = db.Column(db.Integer, nullable=False)
    reference_id = db.Column(db.String(100), nullable=True)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


