from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.job_service import JobService
from app.utils.decorators import role_required

bp = Blueprint('jobs', __name__, url_prefix='/api/jobs')

@bp.route('', methods=['POST'])
@jwt_required()
@role_required('customer')
def create_job():
    try:
        customer_id = get_jwt_identity()
        data = request.get_json()
        
        job = JobService.create_job(
            customer_id=customer_id,
            category_id=data['category_id'],
            title=data['title'],
            description=data['description'],
            location=data['location'],
            budget=data['budget'],
            scheduled_date=data.get('scheduled_date')
        )
        
        return jsonify({'message': 'Job created', 'job_id': job.id}), 201
    except Exception as e:
        return jsonify({'error': 'Failed to create job'}), 500

@bp.route('/<job_id>/accept', methods=['POST'])
@jwt_required()
@role_required('worker')
def accept_job(job_id):
    try:
        user_id = get_jwt_identity()
        from app.models import Worker
        worker = Worker.query.filter_by(user_id=user_id).first_or_404()
        
        job = JobService.accept_job(job_id, worker.id)
        
        return jsonify({'message': 'Job accepted', 'job_id': job.id}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to accept job'}), 500

@bp.route('/<job_id>/status', methods=['PATCH'])
@jwt_required()
def update_status(job_id):
    try:
        data = request.get_json()
        job = JobService.update_job_status(job_id, data['status'])
        return jsonify({'message': 'Status updated', 'status': job.status}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Status update error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp.route('/flagged-workers', methods=['GET'])
@jwt_required()
@role_required('admin')
def get_flagged_workers():
    """Admin: view workers flagged for off-platform payments"""
    from app.models import Worker, User
    workers = Worker.query.filter_by(flagged_for_review=True).all()
    return jsonify({
        'flagged_workers': [{
            'worker_id': w.id,
            'user_id': w.user_id,
            'total_jobs_completed': w.total_jobs_completed,
            'rating': str(w.rating)
        } for w in workers]
    }), 200

@bp.route('/<job_id>', methods=['GET'])
@jwt_required()
def get_job(job_id):
    try:
        from app.models import Job
        job = Job.query.get_or_404(job_id)
        
        return jsonify({
            'id': job.id,
            'title': job.title,
            'description': job.description,
            'budget': str(job.budget),
            'status': job.status,
            'location': job.location
        }), 200
    except Exception as e:
        return jsonify({'error': 'Job not found'}), 404
