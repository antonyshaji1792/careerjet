import time
import logging
from datetime import datetime
from flask import current_app
from app.extensions import db
from app.models.ai_usage import AIUsageLog
from app.services.llm_service import ask_ai
from app.services.credit_service import CreditService

from app.utils.credit_config import get_credit_cost, check_low_credit_warning

logger = logging.getLogger(__name__)

class AIMeteringService:
    """
    Wrapper for AI API calls that handles usage tracking and credit consumption.
    """

    @staticmethod
    async def ask_ai_metered(user_id, feature_type, prompt, system_prompt="You are a helpful assistant.", **kwargs):
        """
        Metered version of ask_ai.
        1. Checks credit balance.
        2. Executes AI call.
        3. Deducts credits on success.
        4. Logs usage.
        """
        cost = get_credit_cost(feature_type)
        
        # 1. Pre-check credits
        balance = CreditService.get_balance(user_id)
        if balance < cost:
            logger.warning(f"User {user_id} insufficient credits for {feature_type}. Has {balance}, needs {cost}")
            return {
                "success": False,
                "error": "insufficient_credits",
                "message": f"Insufficient credits. This feature requires {cost} credits, but you only have {balance}. Please upgrade your plan or top up your credits.",
                "required": cost,
                "current": balance
            }

        start_time = time.time()
        log = AIUsageLog(
            user_id=user_id,
            feature_type=feature_type,
            credits_used=0, # Initially 0
            status='pending'
        )
        db.session.add(log)
        db.session.commit()

        try:
            # 2. Execute AI call
            response = await ask_ai(prompt, system_prompt=system_prompt, **kwargs)
            
            execution_time = time.time() - start_time
            text = response.get('text')
            model = response.get('model')
            usage = response.get('usage', {})
            tokens = usage.get('total_tokens', 0)

            # 3. Deduct credits on success
            success, new_balance = CreditService.deduct_credits(
                user_id=user_id,
                amount=cost,
                feature_name=feature_type,
                metadata={'log_id': log.id, 'tokens': tokens}
            )

            if not success:
                # This should theoretically not happen due to pre-check and locking
                raise ValueError("Credit deduction failed although pre-check passed.")

            # 4. Update Log
            log.status = 'success'
            log.credits_used = cost
            log.ai_model = model
            log.tokens_used = tokens
            log.execution_time = execution_time
            db.session.commit()

            return {
                "success": True,
                "text": text,
                "credits_used": cost,
                "remaining_balance": new_balance
            }

        except Exception as e:
            execution_time = time.time() - start_time
            db.session.rollback()
            
            # Log failure
            failed_log = AIUsageLog.query.get(log.id)
            if failed_log:
                failed_log.status = 'failed'
                failed_log.error_message = str(e)
                failed_log.execution_time = execution_time
                db.session.commit()
            
            logger.error(f"Metered AI call failed for user {user_id}, feature {feature_type}: {str(e)}")
            return {
                "success": False,
                "error": "api_error",
                "message": "An error occurred while processing your request. Credits were not deducted.",
                "details": str(e)
            }
