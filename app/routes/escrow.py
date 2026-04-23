from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.services.escrow_service import EscrowService
from app.services.job_service import JobService
from app.utils.decorators import role_required

bp = Blueprint('escrow', __name__, url_prefix='/api/escrow')


# ── Step 1: Create job + pre-authorize ───────────────────────────────────────

@bp.route('/jobs/create', methods=['POST'])
@jwt_required()
@role_required('customer')
def create_job():
    try:
        customer_id = get_jwt_identity()
        data        = request.get_json()

        job = JobService.create_job(
            customer_id  = customer_id,
            category_id  = data['category_id'],
            title        = data['title'],
            description  = data['description'],
            location     = data['location'],
            budget       = data['budget'],
            scheduled_date = data.get('scheduled_date')
        )

        payment = EscrowService.pre_authorize(job.id, customer_id)

        return jsonify({
            'message':       'Job created and payment pre-authorized',
            'job_id':        job.id,
            'amount':        str(payment.amount),
            'commission':    str(payment.commission),
            'worker_payout': str(payment.worker_payout),
            'escrow_status': payment.status,
            'job_status':    job.status
        }), 201

    except (KeyError, TypeError) as e:
        return jsonify({'error': f'Missing field: {e}'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Step 2: Worker accepts + hold payment ────────────────────────────────────

@bp.route('/jobs/<job_id>/accept', methods=['POST'])
@jwt_required()
@role_required('worker')
def accept_job(job_id):
    try:
        user_id = get_jwt_identity()
        from app.models.worker import Worker
        worker = Worker.query.filter_by(user_id=user_id).first_or_404()

        job     = JobService.accept_job(job_id, worker.id)
        payment = EscrowService.hold_payment(job_id)

        return jsonify({
            'message':       'Job accepted and payment held in escrow',
            'job_id':        job.id,
            'escrow_status': payment.status,
            'job_status':    job.status,
            'amount_held':   str(payment.amount)
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Step 3: Worker marks job complete ────────────────────────────────────────

@bp.route('/jobs/<job_id>/complete', methods=['POST'])
@jwt_required()
@role_required('worker')
def complete_job(job_id):
    try:
        job = JobService.update_job_status(job_id, 'completed')

        from app.services.notification_service import NotificationService
        NotificationService.notify_job_completed(job)

        return jsonify({
            'message':       'Job marked as completed. Waiting for customer approval.',
            'job_id':        job.id,
            'job_status':    job.status,
            'escrow_status': 'held'
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Step 4: Customer approves + release payment ───────────────────────────────

@bp.route('/jobs/<job_id>/approve', methods=['POST'])
@jwt_required()
@role_required('customer')
def approve_payment(job_id):
    try:
        customer_id = get_jwt_identity()
        payment     = EscrowService.release_payment(job_id, customer_id)

        return jsonify({
            'message':       'Payment released to worker',
            'job_id':        job_id,
            'worker_payout': str(payment.worker_payout),
            'commission':    str(payment.commission),
            'escrow_status': payment.status,
            'released_at':   payment.released_at.isoformat()
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Step 5: Cancel + refund ───────────────────────────────────────────────────

@bp.route('/jobs/<job_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_job(job_id):
    try:
        requester_id   = get_jwt_identity()
        requester_role = get_jwt().get('role')
        payment        = EscrowService.refund_payment(job_id, requester_id, requester_role)

        return jsonify({
            'message':       'Job cancelled and payment refunded',
            'job_id':        job_id,
            'escrow_status': payment.status,
            'refunded':      str(payment.amount) if payment.status == 'refunded' else '0'
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Step 6: Customer raises dispute ──────────────────────────────────────────

@bp.route('/jobs/<job_id>/dispute', methods=['POST'])
@jwt_required()
@role_required('customer')
def raise_dispute(job_id):
    try:
        customer_id = get_jwt_identity()
        data        = request.get_json()
        reason      = data.get('reason', 'No reason provided')
        payment     = EscrowService.raise_dispute(job_id, customer_id, reason)

        return jsonify({
            'message':        'Dispute raised. Admin will review.',
            'job_id':         job_id,
            'escrow_status':  payment.status,
            'dispute_reason': payment.dispute_reason
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Step 7: Admin resolves dispute ───────────────────────────────────────────

@bp.route('/admin/disputes/<job_id>/resolve', methods=['POST'])
@jwt_required()
@role_required('admin')
def resolve_dispute(job_id):
    try:
        data               = request.get_json()
        refund_percentage  = data.get('refund_percentage', 0)
        resolution_note    = data.get('resolution', 'Resolved by admin')

        payment, refund_amount, net_payout = EscrowService.resolve_dispute(
            job_id, refund_percentage, resolution_note
        )

        return jsonify({
            'message':          'Dispute resolved',
            'job_id':           job_id,
            'refund_percentage': refund_percentage,
            'customer_refund':  str(refund_amount),
            'worker_payout':    str(net_payout),
            'commission':       str(payment.commission),
            'resolution_note':  resolution_note,
            'escrow_status':    payment.status
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ── Status check ──────────────────────────────────────────────────────────────

@bp.route('/jobs/<job_id>/status', methods=['GET'])
@jwt_required()
def escrow_status(job_id):
    try:
        return jsonify(EscrowService.get_escrow_status(job_id)), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
