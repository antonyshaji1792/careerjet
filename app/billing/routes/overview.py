from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models.subscription import Subscription, Plan
from app.models.credits import CreditWallet, CreditTransaction
from app.services.credit_service import CreditService
from sqlalchemy import func
from datetime import datetime, timedelta

bp = Blueprint('billing_overview', __name__, url_prefix='/api/billing')

@bp.route('/overview', methods=['GET'])
@login_required
def get_overview():
    """
    Consolidated billing and credit overview for the frontend.
    """
    # 1. Subscription Info
    sub = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.created_at.desc()).first()
    plan = Plan.query.get(sub.plan_id) if sub else None
    
    # 2. Credit Info
    balance = CreditService.get_balance(current_user.id)
    daily_usage = CreditService.get_daily_usage(current_user.id)
    
    # 3. Monthly Usage Stats
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    monthly_usage = db.session.query(func.sum(CreditTransaction.credits)).filter(
        CreditTransaction.user_id == current_user.id,
        CreditTransaction.type == 'usage',
        CreditTransaction.credits < 0,
        CreditTransaction.created_at >= thirty_days_ago
    ).scalar() or 0

    return jsonify({
        'subscription': {
            'active': sub.status == 'active' if sub else False,
            'plan_name': plan.name if plan else 'Free Tier',
            'status': sub.status if sub else 'none',
            'renewal_date': sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
        },
        'credits': {
            'balance': balance,
            'daily_usage': daily_usage,
            'monthly_usage': abs(monthly_usage),
            'currency': 'INR'
        }
    })

@bp.route('/credit-history', methods=['GET'])
@login_required
def get_credit_history():
    """
    Detailed credit transaction history.
    """
    transactions = CreditTransaction.query.filter_by(user_id=current_user.id)\
        .order_by(CreditTransaction.created_at.desc())\
        .limit(50).all()
        
    return jsonify([{
        'id': t.id,
        'type': t.type,
        'credits': t.credits,
        'description': t.description,
        'date': t.created_at.isoformat(),
        'reference_id': t.reference_id if t.type == 'topup' else None # Hide internal ref IDs for usage
    } for t in transactions])

@bp.route('/subscription-history', methods=['GET'])
@login_required
def get_subscription_history():
    """
    History of subscription changes.
    """
    subscriptions = Subscription.query.filter_by(user_id=current_user.id)\
        .order_by(Subscription.created_at.desc()).all()
        
    history = []
    for s in subscriptions:
        p = Plan.query.get(s.plan_id)
        history.append({
            'id': s.id,
            'plan_name': p.name if p else 'Unknown',
            'status': s.status,
            'period_start': s.current_period_start.isoformat() if s.current_period_start else None,
            'period_end': s.current_period_end.isoformat() if s.current_period_end else None,
            'created_at': s.created_at.isoformat()
        })
        
    return jsonify(history)

# Internal helper to access db from extensions
from app.extensions import db
