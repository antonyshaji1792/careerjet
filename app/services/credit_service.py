import logging
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.credits import CreditWallet, CreditTransaction
from app.billing.utils.logging import BillingLogger, EVENT_CREDIT_DEDUCTION_FAILURE

logger = logging.getLogger(__name__)


class CreditService:
    """
    Handles all operations related to user credits.
    Uses atomic DB transactions to prevent race conditions.
    """

    @staticmethod
    def get_balance(user_id):
        """Returns current credit balance for a user."""
        wallet = CreditWallet.query.filter_by(user_id=user_id).first()
        if not wallet:
            # Lazy initialize wallet
            wallet = CreditService._initialize_wallet(user_id)
        return wallet.balance_credits

    @staticmethod
    def get_daily_usage(user_id):
        """Returns total credits spent by user today."""
        today = datetime.utcnow().date()
        usage = db.session.query(func.sum(CreditTransaction.credits)).filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.type == 'usage',
            CreditTransaction.credits < 0,
            func.date(CreditTransaction.created_at) == today
        ).scalar() or 0
        return abs(usage)


    @staticmethod
    def add_credits(user_id, amount, transaction_type, reason=None, metadata=None, reference_id=None):
        """
        Adds credits to a user's wallet.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        wallet = CreditWallet.query.filter_by(user_id=user_id).with_for_update().first()
        if not wallet:
            wallet = CreditService._initialize_wallet(user_id)
            # Re-fetch with lock
            wallet = CreditWallet.query.filter_by(user_id=user_id).with_for_update().first()

        try:
            wallet.balance_credits += amount
            
            transaction = CreditTransaction(
                user_id=user_id,
                credits=amount,
                type=transaction_type,
                description=reason,
                reference_id=reference_id
            )
            db.session.add(transaction)
            db.session.commit()
            return wallet.balance_credits
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to add credits to user {user_id}: {str(e)}")
            raise

    @staticmethod
    def deduct_credits(user_id, amount, feature_name, metadata=None, reference_id=None):
        """
        Deducts credits for a feature usage.
        NEVER allows balance to go negative.
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        wallet = CreditWallet.query.filter_by(user_id=user_id).with_for_update().first()
        if not wallet or wallet.balance_credits < amount:
            current_balance = getattr(wallet, 'balance_credits', 0)
            BillingLogger.warning(
                EVENT_CREDIT_DEDUCTION_FAILURE,
                f"Insufficient credits for user {user_id}",
                user_id=user_id,
                required=amount,
                balance=current_balance,
                feature=feature_name
            )
            return False, current_balance


        try:
            wallet.balance_credits -= amount
            
            transaction = CreditTransaction(
                user_id=user_id,
                credits=-amount,
                type='usage',
                description=feature_name,
                reference_id=reference_id
            )
            db.session.add(transaction)
            db.session.commit()
            return True, wallet.balance_credits
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to deduct credits for user {user_id}: {str(e)}")
            raise

    @staticmethod
    def handle_subscription_reset(user_id, plan):
        """
        Resets credits upon monthly renewal.
        """
        wallet = CreditWallet.query.filter_by(user_id=user_id).with_for_update().first()
        if not wallet:
            wallet = CreditService._initialize_wallet(user_id)
            wallet = CreditWallet.query.filter_by(user_id=user_id).with_for_update().first()

        old_balance = wallet.balance_credits
        new_allocation = plan.monthly_credits
        
        # Calculate new balance (Assuming no rollover for now as per simple schema, 
        # but we can implement it if needed. The request didn't mention rollover.)
        
        # Expiration of old credits
        if old_balance > 0:
            exp_trans = CreditTransaction(
                user_id=user_id,
                credits=-old_balance,
                type='usage', # or 'subscription' with negative? User said subscription, usage, topup, admin_adjustment
                description='monthly_reset'
            )
            db.session.add(exp_trans)
        
        wallet.balance_credits = new_allocation
        
        grant_trans = CreditTransaction(
            user_id=user_id,
            credits=new_allocation,
            type='subscription',
            description=f'Plan: {plan.name}'
        )
        db.session.add(grant_trans)
        db.session.commit()
        return wallet.balance_credits

    @staticmethod
    def _initialize_wallet(user_id):
        """Internal helper to create a wallet if missing."""
        try:
            wallet = CreditWallet(user_id=user_id, balance_credits=0)
            db.session.add(wallet)
            db.session.commit()
            return wallet
        except IntegrityError:
            db.session.rollback()
            return CreditWallet.query.filter_by(user_id=user_id).first()
