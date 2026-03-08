from app.models.credits import CreditWallet
from app.services.credit_service import CreditService

# Config-driven credit costs for AI features
AI_FEATURE_COSTS = {
    'resume_generation': 10,
    'resume_optimization': 5,
    'interview_coach': 2,
    'video_interview_question': 1,
    'video_interview_evaluation': 5,
    'cover_letter': 5,
    'skill_gap_analysis': 3,
    'resume_coach': 2,
    'auto_apply': 1,
    'salary_coach': 5
}


# Warning thresholds
LOW_CREDIT_THRESHOLD_PERCENT = 0.20 # 20% of base allocation or fixed threshold

def get_credit_cost(feature_type):
    """
    Retrieve cost for a specific feature.
    Checks SystemConfig for database override first, then falls back to hardcoded config.
    """
    from app.models.config import SystemConfig
    
    # Try database override first
    config_key = f"CREDIT_COST_{feature_type.upper()}"
    db_cost = SystemConfig.get_config_value(config_key)
    if db_cost:
        try:
            return int(db_cost)
        except (ValueError, TypeError):
            pass

    return AI_FEATURE_COSTS.get(feature_type, 1)

def check_low_credit_warning(user_id, feature_type):
    """
    Checks if user is nearing zero credits for a specific feature.
    Returns (is_low, current_balance, cost)
    """
    cost = get_credit_cost(feature_type)
    balance = CreditService.get_balance(user_id)
    
    # Simple logic: If balance is less than 5x the cost, it's low
    # Or specifically if it's below a certain number
    is_low = balance > 0 and balance < (cost * 5)
    
    return is_low, balance, cost
