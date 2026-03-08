from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.integrations.razorpay_client import RazorpayClient
from app.services.credit_service import CreditService
from app.models.credits import CreditTransaction
from app.extensions import db
from app.billing.utils.logging import BillingLogger, EVENT_PAYMENT_FAILURE
import logging

import hmac
import hashlib
import os

logger = logging.getLogger(__name__)

bp = Blueprint('billing_topups', __name__, url_prefix='/billing/topups')

# Configuration for Top-up Packs
TOPUP_PACKS = {
    'starter_pack': {'amount': 199, 'credits': 200, 'name': 'Starter Pack'},
    'value_pack': {'amount': 499, 'credits': 600, 'name': 'Value Pack'},
    'enterprise_pack': {'amount': 999, 'credits': 1500, 'name': 'Elite Pack'}
}

@bp.route('/create-order', methods=['POST'])
@login_required
def create_order():
    """
    Step 1: Create a Razorpay Order for a top-up pack.
    """
    data = request.get_json() or {}
    pack_id = data.get('pack_id')

    if pack_id not in TOPUP_PACKS:
        return jsonify({'error': 'Invalid pack_id'}), 400

    pack = TOPUP_PACKS[pack_id]
    client = RazorpayClient.get_client()

    try:
        # Amount is in paise (₹1 = 100 paise)
        order_data = {
            'amount': pack['amount'] * 100,
            'currency': 'INR',
            'receipt': f"topup_{current_user.id}_{int(os.times().elapsed)}",
            'notes': {
                'user_id': current_user.id,
                'pack_id': pack_id,
                'credits': pack['credits']
            }
        }
        
        razor_order = client.order.create(data=order_data)
        
        logger.info(f"Razorpay Top-up Order {razor_order['id']} created for user {current_user.id}")
        
        return jsonify({
            'order_id': razor_order['id'],
            'amount': order_data['amount'],
            'currency': 'INR',
            'pack_name': pack['name']
        }), 201

    except Exception as e:
        BillingLogger.error(EVENT_PAYMENT_FAILURE, f"Failed to create Razorpay top-up order: {str(e)}", user_id=current_user.id, pack_id=pack_id)
        return jsonify({'error': f"Failed to initiate purchase: {str(e)}"}), 500

@bp.route('/verify-payment', methods=['POST'])
@login_required
def verify_payment():
    """
    Step 2: Verify Razorpay Payment signature and add credits.
    """
    data = request.get_json() or {}
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    pack_id = data.get('pack_id')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature, pack_id]):
        return jsonify({'error': 'Missing payment verification details'}), 400

    if pack_id not in TOPUP_PACKS:
        return jsonify({'error': 'Invalid pack_id'}), 400

    # 1. Verify Signature
    key_secret = os.getenv('RAZORPAY_KEY_SECRET')
    generated_signature = hmac.new(
        key_secret.encode(),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(generated_signature, razorpay_signature):
        BillingLogger.warning(
            EVENT_PAYMENT_FAILURE, 
            "Invalid Razorpay payment signature", 
            order_id=razorpay_order_id, 
            payment_id=razorpay_payment_id,
            user_id=current_user.id
        )
        return jsonify({'error': 'Invalid payment signature'}), 400

    # 2. Check for Idempotency: Has this payment ID been processed?
    existing_trans = CreditTransaction.query.filter_by(
        reference_id=razorpay_payment_id
    ).first()
    
    if existing_trans:
        return jsonify({'message': 'Payment already processed', 'success': True}), 200

    # 3. Add Credits
    pack = TOPUP_PACKS[pack_id]
    try:
        CreditService.add_credits(
            user_id=current_user.id,
            amount=pack['credits'],
            transaction_type='topup',
            reason=f"Top-up Pack: {pack['name']}",
            reference_id=razorpay_payment_id
        )
        
        logger.info(f"Successfully credited {pack['credits']} to user {current_user.id} via top-up {razorpay_payment_id}")
        
        return jsonify({
            'success': True,
            'message': f"Added {pack['credits']} credits to your wallet.",
            'new_balance': CreditService.get_balance(current_user.id)
        }), 200

    except Exception as e:
        logger.error(f"Failed to grant credits for payment {razorpay_payment_id}: {str(e)}")
        return jsonify({'error': 'Payment verified but failed to add credits. Please contact support.'}), 500
