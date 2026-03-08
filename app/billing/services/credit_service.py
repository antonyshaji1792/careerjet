import logging
from datetime import datetime
from app.extensions import db
from app.models.credits import CreditWallet, CreditTransaction
from app.models.subscription import Plan, Subscription
from sqlalchemy import func

logger = logging.getLogger(__name__)

class BillingCreditService:
    """
    High-level credit allocation and reset logic for billing events.
    Complements the core CreditService by handling specific plan rules.
    """

    @staticmethod
    def allocate_subscription_credits(user_id, plan_id):
        """
        Allocates credits on subscription activation.
        Ensures no double allocation for the same period if called multiple times.
        """
        plan = Plan.query.get(plan_id)
        if not plan:
            logger.error(f"Plan {plan_id} not found for credit allocation.")
            return False

        wallet = CreditWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            wallet = CreditWallet(user_id=user_id, balance_credits=0)
            db.session.add(wallet)
            db.session.flush()

        # Check for double allocation: Has the user received a subscription grant in the last 24h?
        # (Simplified check; in production you'd check against the specific billing cycle/invoice)
        last_grant = CreditTransaction.query.filter_by(
            user_id=user_id, 
            type='subscription'
        ).order_by(CreditTransaction.created_at.desc()).first()

        if last_grant and (datetime.utcnow() - last_grant.created_at).total_seconds() < 3600:
            logger.info(f"Subscription credits already allocated for user {user_id} recently. Skipping.")
            return True

        wallet.balance_credits += plan.monthly_credits
        
        transaction = CreditTransaction(
            user_id=user_id,
            type='subscription',
            credits=plan.monthly_credits,
            description=f"Initial allocation for {plan.name}"
        )
        db.session.add(transaction)
        db.session.commit()
        
        logger.info(f"Allocated {plan.monthly_credits} credits to user {user_id} for plan {plan.name}")
        return True

    @staticmethod
    def reset_monthly_credits(user_id):
        """
        Resets subscription credits on monthly renewal.
        Expires unused subscription credits but RETAINS top-up credits.
        """
        sub = Subscription.query.filter_by(user_id=user_id, status='active').first()
        if not sub:
            logger.warning(f"No active subscription found for user {user_id} during credit reset.")
            return False

        plan = Plan.query.get(sub.plan_id)
        wallet = CreditWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            logger.error(f"Credit wallet not found for user {user_id}")
            return False

        # 1. Identify the last subscription grant
        last_grant = CreditTransaction.query.filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.type == 'subscription',
            CreditTransaction.credits > 0
        ).order_by(CreditTransaction.created_at.desc()).first()

        if not last_grant:
            # If no previous grant, just add new plan credits
            wallet.balance_credits += plan.monthly_credits
        else:
            # 2. Calculate usage since the last grant
            usage_sum = db.session.query(func.sum(CreditTransaction.credits)).filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.type == 'usage',
                CreditTransaction.created_at > last_grant.created_at
            ).scalar() or 0
            
            # Use absolute value for usage (since usage is negative)
            credits_used = abs(usage_sum)
            
            # 3. Determine how many "plan credits" are remaining
            # In our logic, plan credits are used FIRST.
            unused_plan_credits = max(0, last_grant.credits - credits_used)
            
            # 4. Calculate Top-up portion
            # Total Balance = (Unused Plan Credits) + (Top-up Credits)
            # Top-up Credits = Total Balance - Unused Plan Credits
            topup_portion = max(0, wallet.balance_credits - unused_plan_credits)
            
            # 5. Reset: New Balance = New Plan Allocation + Top-up Portion
            old_balance = wallet.balance_credits
            wallet.balance_credits = plan.monthly_credits + topup_portion
            
            # 6. Log expiration for audit
            if unused_plan_credits > 0:
                expiration_trans = CreditTransaction(
                    user_id=user_id,
                    type='usage',
                    credits=-unused_plan_credits,
                    description="Expiration of unused monthly credits"
                )
                db.session.add(expiration_trans)

        # 7. Log new grant
        new_grant = CreditTransaction(
            user_id=user_id,
            type='subscription',
            credits=plan.monthly_credits,
            description=f"Monthly renewal allocation for {plan.name}"
        )
        db.session.add(new_grant)
        db.session.commit()
        
        logger.info(f"Reset credits for user {user_id}. New balance: {wallet.balance_credits}")
        return True
