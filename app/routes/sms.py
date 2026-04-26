from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.services.sms_service import SMSService
from app.models import User, Worker
from app.services.job_service import JobService
from app.utils.decorators import role_required

bp = Blueprint('sms', __name__, url_prefix='/api/sms')

sms_service = SMSService()

@bp.route('/callback', methods=['POST'])
def sms_callback():
    try:
        data = request.get_json() or request.form.to_dict()
        phone = data.get('from')
        text = data.get('text')
        message_id = data.get('id')
        
        result = sms_service.handle_incoming_sms(phone, text, message_id)
        
        if result['action'] == 'accept_job':
            user = User.query.filter_by(phone=phone).first()
            if user and user.role == 'worker':
                worker = Worker.query.filter_by(user_id=user.id).first()
                if worker:
                    try:
                        job = JobService.accept_job(result['job_id'], worker.id)
                        sms_service.send_sms(phone, f"Job accepted! Job ID: {job.id[:8]}")
                    except Exception as e:
                        sms_service.send_sms(phone, f"Failed: {str(e)}")
        
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/send', methods=['POST'])
@jwt_required()
@role_required('admin')
def send_sms():
    try:
        data = request.get_json()
        success = sms_service.send_sms(data.get('phone'), data.get('message'))
        return jsonify({'status': 'sent' if success else 'failed'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
