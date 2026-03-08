from functools import wraps
from flask import jsonify, current_app
from flask_login import current_user
from app.services.credit_service import CreditService
from app.utils.credit_config import get_credit_cost
from app.models.config import SystemConfig

def require_credits(feature_type):
    """
    Decorator to ensure a user has enough credits and hasn't hit their daily cap.
    Automatically deducts credits if the function completes successfully.
    """
    def decorator(f):
         @wraps(f)
         def decorated_function(*args, **kwargs):
             if not current_user.is_authenticated:
                 return jsonify({'error': 'Authentication required'}), 401

             # 1. Get Cost
             cost = get_credit_cost(feature_type)
             
             # 2. Check Daily Cap
             daily_cap = int(SystemConfig.get_config_value('AI_DAILY_CREDIT_CAP', default='200'))
             current_daily_usage = CreditService.get_daily_usage(current_user.id)
             
             if current_daily_usage + cost > daily_cap:
                 return jsonify({
                     'error': 'Daily AI usage cap reached',
                     'cap': daily_cap,
                     'current_usage': current_daily_usage
                 }), 403

             # 3. Check Balance & Deduct
             # Note: We deduct BEFORE the feature runs to ensure atomicity and prevent race conditions.
             # If the feature fails, we could optionally refund, but most AI systems deduct on request.
             success, new_balance = CreditService.deduct_credits(
                 user_id=current_user.id,
                 amount=cost,
                 feature_name=feature_type
             )

             if not success:
                 return jsonify({
                     'error': 'Insufficient AI credits',
                     'required': cost,
                     'current_balance': new_balance
                 }), 403

             # 4. Proceed with feature
             try:
                 return f(*args, **kwargs)
             except Exception as e:
                 # Optional: Rollback/Refund logic could go here if the AI actually failed to generate
                 current_app.logger.error(f"Error in credit-protected feature {feature_type}: {str(e)}")
                 raise

         return decorated_function
    return decorator
