from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.subscription import Subscription, Plan
from app.models.credits import CreditWallet, CreditTransaction
from app.models.audit_log import AuditLog
from app.extensions import db
from app.routes.admin import admin_required
import json
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('billing_admin', __name__, url_prefix='/api/admin/billing')

@bp.route('/subscriptions', methods=['GET'])
@login_required
@admin_required
def list_all_subscriptions():
    """
    View all user subscriptions.
    """
    subs = Subscription.query.order_by(Subscription.created_at.desc()).all()
    results = []
    for s in subs:
        plan = Plan.query.get(s.plan_id)
        results.append({
            'sub_id': s.id,
            'user_id': s.user_id,
            'user_email': s.user.email,
            'plan_name': plan.name if plan else 'Unknown',
            'status': s.status,
            'razorpay_id': s.razorpay_subscription_id,
            'current_period_end': s.current_period_end.isoformat() if s.current_period_end else None,
            'created_at': s.created_at.isoformat()
        })
    return jsonify(results)

@bp.route('/credits/<int:user_id>', methods=['GET'])
@login_required
@admin_required
def view_user_credits(user_id):
    """
    Detailed credit usage for a specific user.
    """
    wallet = CreditWallet.query.filter_by(user_id=user_id).first()
    transactions = CreditTransaction.query.filter_by(user_id=user_id)\
        .order_by(CreditTransaction.created_at.desc()).all()
        
    return jsonify({
        'balance': wallet.balance_credits if wallet else 0,
        'history': [{
            'id': t.id,
            'type': t.type,
            'credits': t.credits,
            'description': t.description,
            'reference_id': t.reference_id,
            'date': t.created_at.isoformat()
        } for t in transactions]
    })

@bp.route('/credits/adjust', methods=['POST'])
@login_required
@admin_required
def adjust_credits():
    """
    Manually add or remove credits from a user's wallet.
    """
    data = request.get_json() or {}
    user_id = data.get('user_id')
    amount = data.get('amount')
    reason = data.get('reason', 'Admin adjustment')
    
    if not user_id or amount is None:
        return jsonify({'error': 'user_id and amount are required'}), 400
        
    wallet = CreditWallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        wallet = CreditWallet(user_id=user_id, balance_credits=0)
        db.session.add(wallet)
        db.session.flush()
        
    wallet.balance_credits += int(amount)
    
    trans = CreditTransaction(
        user_id=user_id,
        type='admin_adjustment',
        credits=amount,
        description=reason
    )
    db.session.add(trans)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action='admin_credit_adjustment',
        details=json.dumps({
            'target_user_id': user_id,
            'amount': amount,
            'reason': reason,
            'new_balance': wallet.balance_credits
        }),
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    logger.info(f"ADMIN ACTION: User {current_user.id} adjusted credits for {user_id} by {amount}. New balance: {wallet.balance_credits}")
    
    return jsonify({
        'message': f'Successfully adjusted credits by {amount}',
        'new_balance': wallet.balance_credits
    })

@bp.route('/subscriptions/<int:sub_id>/suspend', methods=['POST'])
@login_required
@admin_required
def suspend_subscription(sub_id):
    """
    Manually suspend a user's subscription.
    """
    sub = Subscription.query.get_or_404(sub_id)
    old_status = sub.status
    sub.status = 'suspended'
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action='admin_subscription_suspend',
        details=json.dumps({
            'subscription_id': sub_id,
            'target_user_id': sub.user_id,
            'razorpay_id': sub.razorpay_subscription_id,
            'old_status': old_status
        }),
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    logger.info(f"ADMIN ACTION: User {current_user.id} suspended subscription {sub_id} for user {sub.user_id}")
    
    return jsonify({'message': f'Subscription {sub_id} suspended successfully'})

@bp.route('/subscriptions/<int:sub_id>/activate', methods=['POST'])
@login_required
@admin_required
def activate_subscription(sub_id):
    """
    Manually activate a user's subscription (e.g. from suspended or pending state).
    """
    sub = Subscription.query.get_or_404(sub_id)
    old_status = sub.status
    sub.status = 'active'
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action='admin_subscription_activate',
        details=json.dumps({
            'subscription_id': sub_id,
            'target_user_id': sub.user_id,
            'razorpay_id': sub.razorpay_subscription_id,
            'old_status': old_status
        }),
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    logger.info(f"ADMIN ACTION: User {current_user.id} activated subscription {sub_id} for user {sub.user_id}")
    
    return jsonify({'message': f'Subscription {sub_id} activated successfully'})

@bp.route('/users/<int:user_id>/change-plan', methods=['POST'])
@login_required
@admin_required
def change_user_plan(user_id):
    """
    Manually change a user's plan.
    This creates a new subscription or updates the current one.
    """
    data = request.get_json() or {}
    plan_id = data.get('plan_id')
    
    if not plan_id:
        return jsonify({'error': 'plan_id is required'}), 400
        
    plan = Plan.query.get_or_404(plan_id)
    
    # Find active subscription or create new one
    sub = Subscription.query.filter_by(user_id=user_id, status='active').first()
    
    old_plan_id = sub.plan_id if sub else None
    
    if sub:
        sub.plan_id = plan.id
        sub.status = 'active' # Ensure it's active if we're changing plan
    else:
        sub = Subscription(
            user_id=user_id,
            plan_id=plan.id,
            status='active',
            current_period_start=db.func.now()
        )
        db.session.add(sub)
    
    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action='admin_change_plan',
        details=json.dumps({
            'target_user_id': user_id,
            'old_plan_id': old_plan_id,
            'new_plan_id': plan.id,
            'subscription_id': sub.id if sub.id else 'new'
        }),
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    logger.info(f"ADMIN ACTION: User {current_user.id} changed plan for user {user_id} to {plan.name}")
    
    return jsonify({
        'message': f'Successfully changed plan to {plan.name}',
        'subscription_id': sub.id
    })


@bp.route('/payments', methods=['GET'])
@login_required
@admin_required
def list_recent_payments():
    """
    View recent payments and top-up references.
    """
    # Focusing on top-ups and subscription charges recorded in transactions
    payments = CreditTransaction.query.filter(
        CreditTransaction.type.in_(['topup', 'subscription']),
        CreditTransaction.credits > 0
    ).order_by(CreditTransaction.created_at.desc()).all()
    
    return jsonify([{
        'user_id': p.user_id,
        'user_email': p.user.email,
        'type': p.type,
        'credits': p.credits,
        'razorpay_ref': p.reference_id,
        'description': p.description,
        'date': p.created_at.isoformat()
    } for p in payments])
