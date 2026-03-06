from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.worker_verification_service import WorkerVerificationService
from app.utils.decorators import role_required
from app.models import Worker

bp = Blueprint('verification', __name__, url_prefix='/api/verification')

@bp.route('/initiate', methods=['POST'])
@jwt_required()
@role_required('worker')
def initiate_verification():
    try:
        user_id = get_jwt_identity()
        worker = Worker.query.filter_by(user_id=user_id).first_or_404()
        
        verification = WorkerVerificationService.initiate_verification(worker.id)
        
        return jsonify({
            'message': 'Verification initiated',
            'verification_id': verification.id,
            'overall_score': verification.overall_score
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/upload-id', methods=['POST'])
@jwt_required()
@role_required('worker')
def upload_national_id():
    try:
        user_id = get_jwt_identity()
        worker = Worker.query.filter_by(user_id=user_id).first_or_404()
        data = request.get_json()
        
        verification = WorkerVerificationService.upload_national_id(
            worker.id,
            data['national_id_number'],
            data['front_url'],
            data['back_url']
        )
        
        return jsonify({
            'message': 'ID uploaded successfully',
            'overall_score': verification.overall_score,
            'flagged': verification.flagged
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/verify-phone', methods=['POST'])
@jwt_required()
@role_required('worker')
def verify_phone():
    try:
        user_id = get_jwt_identity()
        worker = Worker.query.filter_by(user_id=user_id).first_or_404()
        data = request.get_json()
        
        verification = WorkerVerificationService.verify_phone(worker.id, data['otp_code'])
        
        return jsonify({
            'message': 'Phone verified',
            'overall_score': verification.overall_score
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/upload-selfie', methods=['POST'])
@jwt_required()
@role_required('worker')
def upload_selfie():
    try:
        user_id = get_jwt_identity()
        worker = Worker.query.filter_by(user_id=user_id).first_or_404()
        data = request.get_json()
        
        verification = WorkerVerificationService.upload_selfie(worker.id, data['selfie_url'])
        
        return jsonify({
            'message': 'Selfie uploaded',
            'face_match_score': verification.face_match_score,
            'overall_score': verification.overall_score,
            'flagged': verification.flagged
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/upload-skills', methods=['POST'])
@jwt_required()
@role_required('worker')
def upload_skill_documents():
    """OPTIONAL: Upload skill documents for bonus points"""
    try:
        user_id = get_jwt_identity()
        worker = Worker.query.filter_by(user_id=user_id).first_or_404()
        data = request.get_json()
        
        verification = WorkerVerificationService.upload_skill_documents(
            worker.id,
            data.get('documents_urls', [])
        )
        
        return jsonify({
            'message': 'Skill documents uploaded (optional bonus)',
            'overall_score': verification.overall_score,
            'auto_approved': verification.auto_approved,
            'manual_review_required': verification.manual_review_required
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/status', methods=['GET'])
@jwt_required()
@role_required('worker')
def get_verification_status():
    try:
        user_id = get_jwt_identity()
        worker = Worker.query.filter_by(user_id=user_id).first_or_404()
        
        from app.models import WorkerVerification
        verification = WorkerVerification.query.filter_by(worker_id=worker.id).first()
        
        if not verification:
            return jsonify({'message': 'Verification not started'}), 404
        
        return jsonify({
            'overall_score': verification.overall_score,
            'id_verified': verification.id_verified,
            'phone_verified': verification.phone_verified,
            'face_verified': verification.face_verified,
            'skill_verified': verification.skill_verified,
            'auto_approved': verification.auto_approved,
            'manual_review_required': verification.manual_review_required,
            'flagged': verification.flagged,
            'flag_reason': verification.flag_reason
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/admin/pending', methods=['GET'])
@jwt_required()
@role_required('admin')
def get_pending_reviews():
    try:
        verifications = WorkerVerificationService.get_pending_reviews()
        
        return jsonify({
            'pending_reviews': [{
                'id': v.id,
                'worker_id': v.worker_id,
                'overall_score': v.overall_score,
                'flagged': v.flagged,
                'flag_reason': v.flag_reason,
                'created_at': v.created_at.isoformat()
            } for v in verifications]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/admin/review/<verification_id>', methods=['POST'])
@jwt_required()
@role_required('admin')
def admin_review(verification_id):
    try:
        admin_id = get_jwt_identity()
        data = request.get_json()
        
        verification = WorkerVerificationService.admin_review(
            verification_id,
            admin_id,
            data['approved'],
            data.get('notes', '')
        )
        
        return jsonify({
            'message': 'Review completed',
            'approved': data['approved']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
