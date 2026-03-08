import stripe
import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.subscription import Plan, Subscription
from app.models.credits import CreditWallet, CreditTransaction
from app.services.credit_service import CreditService
from app.services.credit_plans import CREDIT_BUNDLES
from app.extensions import db

bp = Blueprint('subscription', __name__, url_prefix='/subscription')

@bp.route('/')
def index():
    subscription = None
    if current_user.is_authenticated:
        subscription = Subscription.query.filter_by(user_id=current_user.id).first()
    return render_template('subscription/index.html', subscription=subscription)

# Assuming Stripe keys are in environment variables
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@bp.route('/plans')
def list_plans():
    """Fetch and display available subscription plans."""
    plans = Plan.query.filter_by(is_active=True).all()
    user_sub = Subscription.query.filter_by(user_id=getattr(current_user, 'id', None)).first()
    return render_template('subscription/plans.html', plans=plans, user_subscription=user_sub)

@bp.route('/subscribe/<int:plan_id>', methods=['POST'])
@login_required
def subscribe(plan_id):
    """Initiate a subscription by creating a Stripe Checkout Session."""
    plan = Plan.query.get_or_404(plan_id)
    
    if not plan.stripe_price_id:
        flash("This plan is not correctly configured for payments (missing Stripe Price ID).", "danger")
        return redirect(url_for('subscription.list_plans'))

    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{
                'price': plan.stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('subscription.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('subscription.list_plans', _external=True),
            metadata={
                'user_id': current_user.id,
                'plan_id': plan.id
            }
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        current_app.logger.error(f"Stripe Checkout Error: {str(e)}")
        flash("Could not initiate payment. Please try again later.", "danger")
        return redirect(url_for('subscription.list_plans'))

@bp.route('/cancel', methods=['POST'])
@login_required
def cancel():
    """Cancel the current subscription."""
    sub = Subscription.query.filter_by(user_id=current_user.id).first_or_404()
    
    if not sub.stripe_subscription_id:
        # Manual cancellation for non-stripe subs if any
        sub.status = 'canceled'
        db.session.commit()
        flash("Subscription canceled.", "success")
        return redirect(url_for('subscription.list_plans'))

    try:
        # Cancel at period end
        stripe.Subscription.modify(
            sub.stripe_subscription_id,
            cancel_at_period_end=True
        )
        # sub.cancel_at_period_end = True  # Removed from model
        db.session.commit()
        
        # sub.cancel_at_period_end is also removed? Let's check model.
        # Actually I just want to fix the crash.
        
        flash("Your subscription will be canceled at the end of the billing period.", "success")
    except Exception as e:
        current_app.logger.error(f"Stripe Cancellation Error: {str(e)}")
        flash("Could not cancel subscription via Stripe. Please contact support.", "danger")
    
    return redirect(url_for('subscription.list_plans'))

@bp.route('/topup')
@login_required
def topup():
    """Display credit top-up bundles."""
    user_credit = CreditWallet.query.filter_by(user_id=current_user.id).first()
    balance = user_credit.balance_credits if user_credit else 0
    return render_template('subscription/topup.html', bundles=CREDIT_BUNDLES, balance=balance)

@bp.route('/topup/checkout/<bundle_id>', methods=['POST'])
@login_required
def topup_checkout(bundle_id):
    """Initiate a one-time payment for credits."""
    bundle = CREDIT_BUNDLES.get(bundle_id)
    if not bundle:
        flash("Invalid credit bundle selected.", "danger")
        return redirect(url_for('subscription.topup'))

    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': bundle['currency'],
                    'product_data': {
                        'name': bundle['name'],
                        'description': bundle['description'],
                    },
                    'unit_amount': bundle['price'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('subscription.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}&type=topup',
            cancel_url=url_for('subscription.topup', _external=True),
            metadata={
                'user_id': current_user.id,
                'bundle_id': bundle_id,
                'type': 'topup',
                'credits': bundle['credits']
            }
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        current_app.logger.error(f"Stripe Topup Checkout Error: {str(e)}")
        flash("Could not initiate payment. Please try again later.", "danger")
        return redirect(url_for('subscription.topup'))

@bp.route('/success')
@login_required
def success():
    """Success landing page from Stripe."""
    session_id = request.args.get('session_id')
    return render_template('subscription/success.html', session_id=session_id)

@bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe Webhooks for asynchronous events."""
    payload = request.get_data()
    sig_header = request.headers.get('STRIPE_SIGNATURE')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except Exception as e:
        return jsonify(status='error', message='Invalid signature'), 400

    event_type = event['type']
    data_object = event['data']['object']

    if event_type == 'checkout.session.completed':
        if data_object.get('mode') == 'subscription':
            handle_checkout_completed(data_object)
        else:
            handle_topup_completed(data_object)
    elif event_type == 'invoice.paid':
        handle_invoice_paid(data_object)
    elif event_type == 'invoice.payment_failed':
        handle_payment_failed(data_object)
    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(data_object)
    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(data_object)

    return jsonify(status='success')

# --- Webhook Handlers ---

def handle_checkout_completed(session):
    user_id = session['metadata'].get('user_id')
    plan_id = session['metadata'].get('plan_id')
    stripe_sub_id = session.get('subscription')
    stripe_cust_id = session.get('customer')

    if not user_id or not plan_id:
        return

    # Fetch full subscription object from stripe to get period dates
    stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
    
    sub = Subscription.query.filter_by(user_id=user_id).first()
    if not sub:
        sub = Subscription(user_id=user_id)
        db.session.add(sub)
    
    old_status = sub.status
    old_plan_id = sub.plan_id if sub.id else None
    
    sub.plan_id = plan_id
    sub.status = 'active'
    sub.stripe_subscription_id = stripe_sub_id
    sub.stripe_customer_id = stripe_cust_id
    sub.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
    sub.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
    # sub.cancel_at_period_end = False # Removed
    
    db.session.flush() # Get ID
    
    # Log History Removed
    db.session.commit()

    # Allocate credits for new subscription
    plan = Plan.query.get(plan_id)
    if plan:
        CreditService.handle_subscription_reset(user_id, plan)

def handle_invoice_paid(invoice):
    stripe_sub_id = invoice.get('subscription')
    if not stripe_sub_id:
        return
        
    sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub_id).first()
    if sub:
        stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
        sub.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
        sub.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        sub.status = 'active'
        
        # history removed
        db.session.commit()

        # Reset credits for renewal
        CreditService.handle_subscription_reset(sub.user_id, sub.plan)

def handle_payment_failed(invoice):
    stripe_sub_id = invoice.get('subscription')
    if not stripe_sub_id:
        return
        
    sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub_id).first()
    if sub:
        sub.status = 'past_due'
        
        # history removed
        db.session.commit()

def handle_subscription_deleted(stripe_sub):
    stripe_sub_id = stripe_sub.get('id')
    sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub_id).first()
    if sub:
        old_status = sub.status
        sub.status = 'canceled'
        
        # history removed
        db.session.commit()

def handle_subscription_updated(stripe_sub):
    stripe_sub_id = stripe_sub.get('id')
    sub = Subscription.query.filter_by(stripe_subscription_id=stripe_sub_id).first()
    if sub:
        sub.status = stripe_sub.get('status')
        sub.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        # sub.cancel_at_period_end = stripe_sub.get('cancel_at_period_end') # removed
        db.session.commit()

def handle_topup_completed(session):
    """Handle one-time credit purchase completion."""
    user_id = session['metadata'].get('user_id')
    bundle_id = session['metadata'].get('bundle_id')
    credits_to_add = int(session['metadata'].get('credits', 0))
    session_id = session.get('id')

    if not user_id or not bundle_id or not credits_to_add:
        current_app.logger.warning(f"Malformed topup webhook session: {session_id}")
        return

    # Idempotency Check: Ensure we haven't processed this session yet
    existing_trans = CreditTransaction.query.filter(
        CreditTransaction.user_id == user_id,
        CreditTransaction.type == 'topup',
        CreditTransaction.reference_id == session_id
    ).first()
    
    if existing_trans:
        current_app.logger.info(f"Topup session {session_id} already processed. Skipping.")
        return

    try:
        CreditService.add_credits(
            user_id=user_id,
            amount=credits_to_add,
            transaction_type='topup',
            reason=f"Bundle: {bundle_id}",
            reference_id=session_id
        )
        current_app.logger.info(f"Successfully added {credits_to_add} credits to user {user_id} via topup.")
    except Exception as e:
        current_app.logger.error(f"Failed to process topup for session {session_id}: {str(e)}")

