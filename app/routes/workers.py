from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.worker_service import WorkerService, haversine_km
from app.utils.decorators import role_required

bp = Blueprint('workers', __name__, url_prefix='/api/workers')

@bp.route('', methods=['POST'])
@jwt_required()
@role_required('worker')
def create_profile():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        worker = WorkerService.create_worker_profile(
            user_id=user_id,
            hourly_rate=data['hourly_rate'],
            location=data['location'],
            bio=data.get('bio'),
            skills=data.get('skills', []),
            latitude=data.get('latitude'),
            longitude=data.get('longitude')
        )
        
        return jsonify({'message': 'Worker profile created', 'worker_id': worker.id}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Worker profile creation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create profile: {str(e)}'}), 500

@bp.route('/search', methods=['GET'])
@jwt_required()
def search_workers():
    try:
        category_id = request.args.get('category_id')
        location = request.args.get('location')
        latitude = request.args.get('latitude', type=float)
        longitude = request.args.get('longitude', type=float)
        radius_km = request.args.get('radius_km', default=20, type=float)
        min_rating = request.args.get('min_rating', type=float)

        workers = WorkerService.search_workers(
            category_id=category_id, location=location,
            latitude=latitude, longitude=longitude,
            min_rating=min_rating, radius_km=radius_km
        )

        return jsonify({
            'workers': [{
                'id': w.id,
                'user_id': w.user_id,
                'hourly_rate': str(w.hourly_rate),
                'location': w.location,
                'latitude': w.latitude,
                'longitude': w.longitude,
                'rating': str(w.rating),
                'total_reviews': w.total_reviews,
                'total_jobs_completed': w.total_jobs_completed,
                'distance_km': round(haversine_km(latitude, longitude, w.latitude, w.longitude), 2)
                    if latitude and longitude and w.latitude and w.longitude else None
            } for w in workers]
        }), 200
    except Exception as e:
        return jsonify({'error': 'Search failed'}), 500

@bp.route('/<worker_id>', methods=['GET'])
def get_worker(worker_id):
    try:
        from app.models import Worker
        worker = Worker.query.get_or_404(worker_id)
        
        return jsonify({
            'id': worker.id,
            'hourly_rate': str(worker.hourly_rate),
            'location': worker.location,
            'bio': worker.bio,
            'rating': str(worker.rating),
            'total_reviews': worker.total_reviews,
            'verification_status': worker.verification_status
        }), 200
    except Exception:
        return jsonify({'error': 'Worker not found'}), 404
