from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.services.credit_service import CreditService
from app.models.credits import CreditTransaction

bp = Blueprint('credits', __name__, url_prefix='/api/credits')

@bp.route('/balance', methods=['GET'])
@login_required
def get_balance():
    """Get current user credit balance."""
    balance = CreditService.get_balance(current_user.id)
    return jsonify({
        'balance': balance,
        'user_id': current_user.id
    })

@bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """Get credit transaction history."""
    limit = request.args.get('limit', 20, type=int)
    transactions = CreditTransaction.query.filter_by(user_id=current_user.id)\
        .order_by(CreditTransaction.created_at.desc())\
        .limit(limit).all()
    
    return jsonify([{
        'id': t.id,
        'credits': t.credits,
        'type': t.type,
        'description': t.description,
        'reference_id': t.reference_id,
        'date': t.created_at.isoformat()
    } for t in transactions])

@bp.route('/check-usage', methods=['POST'])
@login_required
def check_usage():
    """Internal style check before using an AI feature."""
    data = request.json
    feature = data.get('feature')
    cost = data.get('cost', 1)
    
    balance = CreditService.get_balance(current_user.id)
    if balance < cost:
        return jsonify({
            'allowed': False,
            'message': 'Insufficient credits',
            'required': cost,
            'current': balance
        }), 403
        
    return jsonify({
        'allowed': True,
        'current': balance
    })
