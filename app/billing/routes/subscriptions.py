from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.models.subscription import Plan, Subscription
from app.integrations.razorpay_client import RazorpayClient
from app.extensions import db
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('billing_subscriptions', __name__, url_prefix='/billing/subscriptions')

@bp.route('/create', methods=['POST'])
@login_required
def create_subscription():
    """
    Create a new Razorpay subscription for the authenticated user.
    """
    data = request.get_json() or {}
    plan_id = data.get('plan_id')
    
    if not plan_id:
        return jsonify({'error': 'plan_id is required'}), 400
        
    plan = Plan.query.get(plan_id)
    if not plan or not plan.is_active:
        return jsonify({'error': 'Invalid or inactive plan'}), 404
        
    if not plan.razorpay_plan_id:
        return jsonify({'error': 'Plan not configured with Razorpay (missing razorpay_plan_id)'}), 400

    # Ensure strictly one active/pending subscription per user
    existing_sub = Subscription.query.filter(
        Subscription.user_id == current_user.id,
        Subscription.status.in_(['active', 'created'])
    ).first()
    
    if existing_sub:
        return jsonify({
            'error': 'User already has an active or pending subscription',
            'subscription_id': existing_sub.razorpay_subscription_id,
            'status': existing_sub.status
        }), 400

    client = RazorpayClient.get_client()
    try:
        # Create Razorpay subscription
        # total_count=12 means 1 year if monthly, or as per plan setup
        razor_sub = client.subscription.create({
            'plan_id': plan.razorpay_plan_id,
            'customer_notify': 1,
            'total_count': 120, # Long term (10 years) for recurring subs
            'addons': []
        })
        
        new_sub = Subscription(
            user_id=current_user.id,
            plan_id=plan.id,
            razorpay_subscription_id=razor_sub['id'],
            status='created'
        )
        db.session.add(new_sub)
        db.session.commit()
        
        logger.info(f"Subscription {razor_sub['id']} created for user {current_user.id}")
        
        return jsonify({
            'message': 'Subscription created successfully',
            'razorpay_subscription_id': razor_sub['id'],
            'status': 'created',
            'short_url': razor_sub.get('short_url')
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Razorpay subscription creation failed for user {current_user.id}: {str(e)}")
        return jsonify({'error': f'Failed to create subscription: {str(e)}'}), 500

@bp.route('/cancel', methods=['POST'])
@login_required
def cancel_subscription():
    """
    Cancel the user's active Razorpay subscription.
    """
    sub = Subscription.query.filter_by(
        user_id=current_user.id, 
        status='active'
    ).first()
    
    if not sub:
        return jsonify({'error': 'No active subscription found to cancel'}), 404

    client = RazorpayClient.get_client()
    try:
        # Cancel Razorpay subscription immediately
        client.subscription.cancel(sub.razorpay_subscription_id, {
            'cancel_at_cycle_end': False
        })
        
        sub.status = 'cancelled'
        db.session.commit()
        
        logger.info(f"Subscription {sub.razorpay_subscription_id} cancelled by user {current_user.id}")
        
        return jsonify({'message': 'Subscription cancelled successfully'}), 200
    except Exception as e:
        logger.error(f"Razorpay subscription cancellation failed for {sub.razorpay_subscription_id}: {str(e)}")
        return jsonify({'error': f'Failed to cancel subscription with Razorpay: {str(e)}'}), 500

@bp.route('/status', methods=['GET'])
@login_required
def subscription_status():
    """
    Get the status of the current user's most recent subscription.
    """
    sub = Subscription.query.filter_by(user_id=current_user.id).order_by(Subscription.created_at.desc()).first()
    
    if not sub:
        return jsonify({'subscription': None}), 200
        
    plan = Plan.query.get(sub.plan_id)
    return jsonify({
        'subscription': {
            'id': sub.id,
            'plan_name': plan.name if plan else 'Unknown',
            'status': sub.status,
            'razorpay_id': sub.razorpay_subscription_id,
            'current_period_start': sub.current_period_start.isoformat() if sub.current_period_start else None,
            'current_period_end': sub.current_period_end.isoformat() if sub.current_period_end else None,
            'created_at': sub.created_at.isoformat(),
            'updated_at': sub.updated_at.isoformat()
        }
    }), 200
