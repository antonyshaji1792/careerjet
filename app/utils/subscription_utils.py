from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user
from datetime import datetime, timedelta

def subscription_required(f):
    """
    Decorator to ensure the user has an active subscription.
    Checks for status and grace period.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        
        subscription = current_user.subscription
        if not subscription:
            flash("This feature requires an active subscription.", "info")
            return redirect(url_for('subscription.list_plans'))
        
        # Check active status with 3-day grace period
        if not subscription.is_active():
            flash("Your subscription is inactive. Please renew to continue.", "warning")
            return redirect(url_for('subscription.list_plans'))
            
        return f(*args, **kwargs)
    return decorated_function

def check_subscription_status(user):
    """Utility to check if user has active subscription without redirecting."""
    if not user.is_authenticated or not user.subscription:
        return False
    return user.subscription.is_active()
