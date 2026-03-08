"""
Feature flags and tier enforcement for monetization.
"""
from functools import wraps
from flask import jsonify
from flask_login import current_user

class FeatureFlags:
    """
    Defines which features are available at each subscription tier.
    """
    
    # Free tier features (baseline)
    FREE = {
        'basic_resume_generation',
        'ats_analysis',
        'pdf_export',
        'health_score',
        'inline_validation',
        'ai_improvement'
    }
    
    # Premium tier features (Free + Premium-only)
    PREMIUM = FREE | {
        'recruiter_personas',           # NEW: Simulate recruiter perspectives
        'interview_probability',        # NEW: Predict interview likelihood
        'resume_analytics',             # NEW: Advanced metrics & trends
        'unlimited_ai_usage',
        'priority_support'
    }
    
    # Enterprise tier features (Premium + Enterprise-only)
    ENTERPRISE = PREMIUM | {
        'bulk_uploads',                 # NEW: Upload multiple resumes at once
        'compliance_mode',              # NEW: GDPR/SOC2 compliant exports
        'white_label_exports',          # NEW: Remove CareerJet branding
        'api_access',
        'sso_integration',
        'dedicated_support'
    }
    
    @staticmethod
    def get_user_features(user):
        """Returns set of features available to the user."""
        if not user or not user.subscription:
            return FeatureFlags.FREE
        
        subscription = user.subscription
        
        if not subscription.is_active():
            return FeatureFlags.FREE
        
        if subscription.is_enterprise():
            return FeatureFlags.ENTERPRISE
        elif subscription.is_premium():
            return FeatureFlags.PREMIUM
        else:
            return FeatureFlags.FREE
    
    @staticmethod
    def has_feature(user, feature_name):
        """Check if user has access to a specific feature."""
        user_features = FeatureFlags.get_user_features(user)
        return feature_name in user_features


def require_premium(f):
    """
    Decorator to enforce Premium or Enterprise tier for route access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'authentication_required',
                'message': 'Please log in to access this feature.'
            }), 401
        
        if not current_user.subscription or not current_user.subscription.is_premium():
            return jsonify({
                'success': False,
                'error': 'premium_required',
                'message': 'This feature requires a Premium or Enterprise subscription.',
                'upgrade_url': '/pricing'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


def require_enterprise(f):
    """
    Decorator to enforce Enterprise tier for route access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': 'authentication_required',
                'message': 'Please log in to access this feature.'
            }), 401
        
        if not current_user.subscription or not current_user.subscription.is_enterprise():
            return jsonify({
                'success': False,
                'error': 'enterprise_required',
                'message': 'This feature is exclusive to Enterprise subscribers.',
                'upgrade_url': '/pricing'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


def check_feature_access(feature_name):
    """
    Decorator factory to check access to a specific feature.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    'success': False,
                    'error': 'authentication_required',
                    'message': 'Please log in to access this feature.'
                }), 401
            
            if not FeatureFlags.has_feature(current_user, feature_name):
                # Determine required tier
                if feature_name in FeatureFlags.ENTERPRISE - FeatureFlags.PREMIUM:
                    tier = 'Enterprise'
                elif feature_name in FeatureFlags.PREMIUM - FeatureFlags.FREE:
                    tier = 'Premium'
                else:
                    tier = 'Unknown'
                
                return jsonify({
                    'success': False,
                    'error': 'feature_locked',
                    'message': f'This feature requires a {tier} subscription.',
                    'required_tier': tier,
                    'upgrade_url': '/pricing'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
