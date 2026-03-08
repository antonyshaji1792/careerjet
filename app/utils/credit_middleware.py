import functools
import inspect
from flask import jsonify, request, flash, redirect, url_for, current_app
from flask_login import current_user
from app.services.credit_service import CreditService
from app.utils.credit_config import get_credit_cost, check_low_credit_warning
from app.models.credits import CreditWallet
from app.models.config import SystemConfig
import logging

logger = logging.getLogger(__name__)

def credit_required(feature_type):

    """
    Decorator for routes that require AI credits.
    - Checks daily usage cap
    - Checks balance
    - Deducts credits atomically before execution
    - Supports both sync and async routes
    """
    def decorator(f):
        def perform_checks():
            if not current_user.is_authenticated:
                return False, ("Authentication required", 401)

            # 1. Get Cost
            cost = get_credit_cost(feature_type)
            
            # 2. Check Daily Cap
            daily_cap = int(SystemConfig.get_config_value('AI_DAILY_CREDIT_CAP', default='200'))
            current_daily_usage = CreditService.get_daily_usage(current_user.id)
            
            if current_daily_usage + cost > daily_cap:
                message = f"Daily AI usage cap reached ({daily_cap} credits). Please try again tomorrow or contact support."
                logger.warning(f"ABUSE PREVENTION: User {current_user.id} hit daily cap ({daily_cap}) attempting {feature_type}")
                return False, (message, 403)

            # 3. Check Balance & Deduct
            success, new_balance = CreditService.deduct_credits(
                user_id=current_user.id,
                amount=cost,
                feature_name=feature_type
            )

            if not success:
                message = f"Insufficient credits! '{feature_type.replace('_', ' ').title()}' requires {cost} credits, but you only have {new_balance}."
                logger.warning(f"ABUSE PREVENTION: User {current_user.id} insufficient credits for {feature_type} (Balance: {new_balance}, Required: {cost})")
                return False, (message, 402) # 402 Payment Required

            return True, (cost, new_balance)

        def handle_error(message, status_code):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    "success": False,
                    "error": "credit_check_failed",
                    "message": message,
                    "topup_url": url_for('subscription.topup', _external=True)
                }), status_code
            
            flash(message, "warning")
            return redirect(url_for('subscription.topup'))

        @functools.wraps(f)
        async def async_wrapper(*args, **kwargs):
            allowed, result = perform_checks()
            if not allowed:
                return handle_error(result[0], result[1])
            return await f(*args, **kwargs)

        @functools.wraps(f)
        def sync_wrapper(*args, **kwargs):
            allowed, result = perform_checks()
            if not allowed:
                return handle_error(result[0], result[1])
            return f(*args, **kwargs)

        if inspect.iscoroutinefunction(f):
            return async_wrapper
        return sync_wrapper

    return decorator
