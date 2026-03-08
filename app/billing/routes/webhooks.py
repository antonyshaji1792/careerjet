from flask import Blueprint, request, jsonify, current_app
from app.integrations.razorpay_client import RazorpayClient
from app.models.subscription import Subscription, Plan
from app.extensions import db, csrf
from datetime import datetime
from app.billing.services.credit_service import BillingCreditService
from app.billing.utils.logging import BillingLogger, EVENT_WEBHOOK_ERROR, EVENT_SUBSCRIPTION_MISMATCH
import json

import logging

logger = logging.getLogger(__name__)

bp = Blueprint('billing_webhooks', __name__, url_prefix='/webhooks')

@bp.route('/razorpay', methods=['POST'])
@csrf.exempt # Webhooks don't have CSRF tokens
def razorpay_webhook():
    """
    Handle Razorpay Webhooks.
    """
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Razorpay-Signature')
    
    if not signature:
        BillingLogger.warning(EVENT_WEBHOOK_ERROR, "Razorpay webhook received without signature")
        return jsonify({'error': 'Missing signature'}), 400

    # 1. Verify Signature
    if not RazorpayClient.verify_webhook_signature(payload, signature):
        BillingLogger.error(EVENT_WEBHOOK_ERROR, "Razorpay webhook signature verification failed", signature=signature)
        return jsonify({'error': 'Invalid signature'}), 400

    # 2. Parse Payload
    try:
        event_data = json.loads(payload)
        event_type = event_data.get('event')
    except Exception as e:
        BillingLogger.error(EVENT_WEBHOOK_ERROR, f"Failed to parse Razorpay webhook payload: {str(e)}", payload=payload)
        return jsonify({'error': 'Invalid payload'}), 400

    # Log full payload for debugging (safely)
    # logger.debug(f"Webhook Payload: {payload}")

    # 3. Handle Events
    try:
        if event_type == 'subscription.activated':
            handle_subscription_activated(event_data)
        elif event_type == 'subscription.charged':
            handle_subscription_charged(event_data)
        elif event_type == 'subscription.cancelled':
            handle_subscription_cancelled(event_data)
        else:
            logger.info(f"Unhandled Razorpay event: {event_type}")

    except Exception as e:
        BillingLogger.error(EVENT_WEBHOOK_ERROR, f"Error processing Razorpay event {event_type}: {str(e)}", event_id=event_data.get('id'))
        return jsonify({'status': 'error', 'message': str(e)}), 500

    return jsonify({'status': 'ok'}), 200

def handle_subscription_activated(data):
    """
    Handle subscription.activated event.
    """
    sub_payload = data['payload']['subscription']['entity']
    razor_sub_id = sub_payload['id']
    
    sub = Subscription.query.filter_by(razorpay_subscription_id=razor_sub_id).first()
    if not sub:
        BillingLogger.warning(EVENT_SUBSCRIPTION_MISMATCH, f"Subscription {razor_sub_id} not found in database for activation")
        return

    sub.status = 'active'
    if sub_payload.get('current_start'):
        sub.current_period_start = datetime.fromtimestamp(sub_payload['current_start'])
    if sub_payload.get('current_end'):
        sub.current_period_end = datetime.fromtimestamp(sub_payload['current_end'])
    
    db.session.commit()
    
    # NEW: Allocate credits on activation
    BillingCreditService.allocate_subscription_credits(sub.user_id, sub.plan_id)
    
    logger.info(f"Subscription {razor_sub_id} activated and credits allocated via webhook.")

def handle_subscription_charged(data):
    """
    Handle subscription.charged event (payment successful).
    """
    sub_payload = data['payload']['subscription']['entity']
    razor_sub_id = sub_payload['id']
    
    sub = Subscription.query.filter_by(razorpay_subscription_id=razor_sub_id).first()
    if not sub:
        logger.warning(f"Subscription {razor_sub_id} not found in database for charged event.")
        return

    # Update period dates and ensure status is active
    sub.status = 'active'
    if sub_payload.get('current_start'):
        sub.current_period_start = datetime.fromtimestamp(sub_payload['current_start'])
    if sub_payload.get('current_end'):
        sub.current_period_end = datetime.fromtimestamp(sub_payload['current_end'])
    
    # Optional: Allocate credits here if you want to do it on every charge
    # For now, let's just update the local record.
    
    db.session.commit()
    
    # NEW: Reset credits on renewal (if paid_count > 1)
    paid_count = sub_payload.get('paid_count', 0)
    if paid_count > 1:
        BillingCreditService.reset_monthly_credits(sub.user_id)
        logger.info(f"Subscription {razor_sub_id} credits reset for renewal via webhook.")
    else:
        # For the first payment, activated event usually handles it,
        # but we can call allocate just in case activated was missed.
        # Our allocation method has a safety check for double allocation.
        BillingCreditService.allocate_subscription_credits(sub.user_id, sub.plan_id)

    logger.info(f"Subscription {razor_sub_id} charged/renewed via webhook.")

def handle_subscription_cancelled(data):
    """
    Handle subscription.cancelled event.
    """
    sub_payload = data['payload']['subscription']['entity']
    razor_sub_id = sub_payload['id']
    
    sub = Subscription.query.filter_by(razorpay_subscription_id=razor_sub_id).first()
    if not sub:
        logger.warning(f"Subscription {razor_sub_id} not found in database for cancellation.")
        return

    sub.status = 'cancelled'
    db.session.commit()
    logger.info(f"Subscription {razor_sub_id} marked as cancelled via webhook.")
