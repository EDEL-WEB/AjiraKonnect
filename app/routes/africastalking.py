from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.utils.decorators import role_required
from app.services.africastalking_service import at_service

bp = Blueprint('africastalking', __name__, url_prefix='/api/at')


@bp.route('/balance', methods=['GET'])
@jwt_required()
@role_required('admin')
def get_balance():
    """GET /api/at/balance — fetch Africa's Talking account balance (admin only)."""
    try:
        data = at_service.get_balance()
        return jsonify({'status': 'success', 'data': data}), 200
    except EnvironmentError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'Failed to fetch balance', 'detail': str(e)}), 502
