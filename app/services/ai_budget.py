import logging
from datetime import datetime, timedelta
from app.models import AIUsageLog, db, Subscription
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)

class AIBudgetService:
    """
    Manages AI usage quotas and handles rate limiting/throttling.
    Limits are defined by action types and user subscription tiers.
    """

    DEFAULT_LIMITS = {
        'Free': {
            'generation': 3,    # Total lifetime or per period
            'regeneration': 5,  # Daily
            'analysis': 5       # Daily
        },
        'Pro': {
            'generation': 50,
            'regeneration': 100,
            'analysis': 200
        }
    }

    @staticmethod
    def check_budget_ok(user_id, action_type):
        """
        Returns (True, None) if the user has remaining quota, 
        else (False, error_message).
        """
        # 1. Get user plan
        sub = Subscription.query.filter_by(user_id=user_id).first()
        plan = sub.plan if sub else 'Free'
        
        limit = AIBudgetService.DEFAULT_LIMITS.get(plan, AIBudgetService.DEFAULT_LIMITS['Free']).get(action_type, 0)
        
        # 2. Get current usage
        usage = AIUsage.query.filter_by(user_id=user_id, action_type=action_type).first()
        
        if not usage:
            return True, None
            
        # 3. Check for reset (Daily limits for specific actions)
        if action_type in ['regeneration', 'analysis']:
            if usage.last_reset.date() < datetime.utcnow().date():
                usage.count = 0
                usage.last_reset = datetime.utcnow()
                db.session.commit()
                return True, None
        
        if usage.count >= limit:
            return False, f"Daily/Total quota for '{action_type}' reached. Upgrade to Pro for high-volume AI usage."
            
        return True, None

    @staticmethod
    def consume_budget(user_id, action_type):
        """
        Increments usage count for a given user and action.
        Uses an upsert logic for concurrency safety.
        """
        try:
            usage = AIUsage.query.filter_by(user_id=user_id, action_type=action_type).first()
            if not usage:
                usage = AIUsage(user_id=user_id, action_type=action_type, count=1)
                db.session.add(usage)
            else:
                usage.count += 1
            
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to increment AI usage: {str(e)}")
            db.session.rollback()
            return False

    @staticmethod
    def get_remaining_quota(user_id, action_type):
        """Helper for UI to show remaining uses."""
        sub = Subscription.query.filter_by(user_id=user_id).first()
        plan = sub.plan if sub else 'Free'
        limit = AIBudgetService.DEFAULT_LIMITS.get(plan, AIBudgetService.DEFAULT_LIMITS['Free']).get(action_type, 0)
        
        usage = AIUsage.query.filter_by(user_id=user_id, action_type=action_type).first()
        if not usage:
            return limit
            
        # Check reset logic
        if action_type in ['regeneration', 'analysis'] and usage.last_reset.date() < datetime.utcnow().date():
            return limit
            
        return max(0, limit - usage.count)
