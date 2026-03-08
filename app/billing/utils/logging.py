import logging
import json
from datetime import datetime

logger = logging.getLogger('billing')

class BillingLogger:
    """
    Standardizes structured logging for financial and billing events.
    Ensures logs are searchable in production environments (e.g., CloudWatch, ELK).
    """
    
    @staticmethod
    def _log(level, event_type, message, **kwargs):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'message': message,
            **kwargs
        }
        # Using a fixed prefix for easy searching/filtering
        logger.log(level, f"[BILLING_EVENT] {json.dumps(log_data)}")

    @classmethod
    def info(cls, event_type, message, **kwargs):
        cls._log(logging.INFO, event_type, message, **kwargs)

    @classmethod
    def warning(cls, event_type, message, **kwargs):
        cls._log(logging.WARNING, event_type, message, **kwargs)

    @classmethod
    def error(cls, event_type, message, **kwargs):
        cls._log(logging.ERROR, event_type, message, **kwargs)

# Event Type Constants for consistency
EVENT_PAYMENT_FAILURE = 'payment_failure'
EVENT_WEBHOOK_ERROR = 'webhook_error'
EVENT_CREDIT_DEDUCTION_FAILURE = 'credit_deduction_failure'
EVENT_SUBSCRIPTION_MISMATCH = 'subscription_mismatch'
EVENT_AUDIT_ADJUSTMENT = 'admin_adjustment'
