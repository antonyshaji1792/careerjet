from datetime import datetime
from app.extensions import db

class Plan(db.Model):
    """
    Subscription plans configurable by admin.
    """
    __tablename__ = 'plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=True)
    razorpay_plan_id = db.Column(db.String(100), unique=True, nullable=True)
    stripe_price_id = db.Column(db.String(100), unique=True, nullable=True)
    monthly_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    monthly_credits = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Float, default=0.0)
    interval = db.Column(db.String(20), default='month')
    credits_per_interval = db.Column(db.Integer, default=0)
    features = db.Column(db.JSON, nullable=True)
    rollover_allowed = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'razorpay_plan_id': self.razorpay_plan_id,
            'stripe_price_id': self.stripe_price_id,
            'monthly_price': float(self.monthly_price),
            'monthly_credits': self.monthly_credits,
            'price': self.price,
            'interval': self.interval,
            'credits_per_interval': self.credits_per_interval,
            'features': self.features,
            'rollover_allowed': self.rollover_allowed,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


    def __repr__(self):
        return f'<Plan {self.name}>'

class Subscription(db.Model):
    """
    Active subscription for a user.
    """
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.id'), nullable=False, index=True)
    razorpay_subscription_id = db.Column(db.String(100), unique=True, nullable=True)
    stripe_subscription_id = db.Column(db.String(100), unique=True, nullable=True)
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='created') # created, active, cancelled, expired
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    plan = db.relationship('Plan', backref='user_subscriptions')

    def is_active(self):
        """Check if subscription is active."""
        if self.status != 'active':
            return False
        if self.current_period_end and datetime.utcnow() > self.current_period_end:
            return False
        return True


