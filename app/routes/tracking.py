from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_socketio import emit, join_room, leave_room
from app import db, socketio
from app.models.tracking import JobTracking
from app.models.job import Job
from app.models import Worker
from datetime import datetime
import math

bp = Blueprint('tracking', __name__, url_prefix='/api/tracking')

ARRIVAL_THRESHOLD_METERS = 10


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two GPS coordinates"""
    R = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def check_arrival(job_id, worker_lat, worker_lng):
    """Check if worker has arrived within 10 meters of job location"""
    job = Job.query.get(job_id)
    if not job or not job.job_latitude or not job.job_longitude:
        return False, 0

    distance = haversine_distance(
        worker_lat, worker_lng,
        job.job_latitude, job.job_longitude
    )
    return distance <= ARRIVAL_THRESHOLD_METERS, round(distance, 1)


# ─── REST Endpoints ───────────────────────────────────────────────────────────

@bp.route('/<job_id>/location', methods=['GET'])
@jwt_required()
def get_last_location(job_id):
    """Get worker's last known location for a job (REST fallback for offline)"""
    location = JobTracking.query.filter_by(job_id=job_id) \
        .order_by(JobTracking.timestamp.desc()).first()

    if not location:
        return jsonify({'error': 'No location data available'}), 404

    return jsonify({
        'latitude': location.latitude,
        'longitude': location.longitude,
        'timestamp': location.timestamp.isoformat()
    }), 200


@bp.route('/<job_id>/history', methods=['GET'])
@jwt_required()
def get_location_history(job_id):
    """Get full location history for a job"""
    locations = JobTracking.query.filter_by(job_id=job_id) \
        .order_by(JobTracking.timestamp.asc()).all()

    return jsonify({
        'history': [{
            'latitude': l.latitude,
            'longitude': l.longitude,
            'timestamp': l.timestamp.isoformat()
        } for l in locations]
    }), 200


@bp.route('/<job_id>/update', methods=['POST'])
@jwt_required()
def update_location_rest(job_id):
    """REST fallback for workers without WebSocket support (feature phones)"""
    user_id = get_jwt_identity()
    worker = Worker.query.filter_by(user_id=user_id).first_or_404()
    data = request.get_json()

    job = Job.query.get_or_404(job_id)
    if job.status not in ['accepted', 'in_progress']:
        return jsonify({'error': 'Job is not active'}), 400

    latitude = data['latitude']
    longitude = data['longitude']

    tracking = JobTracking(
        job_id=job_id,
        worker_id=worker.id,
        latitude=latitude,
        longitude=longitude
    )
    db.session.add(tracking)
    db.session.commit()

    # Check arrival
    arrived, distance = check_arrival(job_id, latitude, longitude)
    payload = {
        'latitude': latitude,
        'longitude': longitude,
        'timestamp': datetime.utcnow().isoformat(),
        'distance_to_job': distance
    }

    if arrived:
        payload['arrived'] = True
        socketio.emit('worker_arrived', {
            'message': 'Worker has arrived!',
            'distance': distance
        }, room=f'job_{job_id}')
    
    socketio.emit('location_update', payload, room=f'job_{job_id}')

    return jsonify({
        'message': 'Location updated',
        'distance_to_job': distance,
        'arrived': arrived
    }), 200


# ─── WebSocket Events ─────────────────────────────────────────────────────────

@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'Connected to KaziConnect tracking'})


@socketio.on('watch_job')
def handle_watch_job(data):
    """Customer joins a job room to receive live location updates"""
    job_id = data.get('job_id')
    join_room(f'job_{job_id}')
    emit('watching', {'message': f'Now tracking job {job_id}'})


@socketio.on('stop_watching')
def handle_stop_watching(data):
    """Customer leaves job room"""
    job_id = data.get('job_id')
    leave_room(f'job_{job_id}')


@socketio.on('worker_location_update')
def handle_location_update(data):
    """
    Worker sends GPS coordinates every 3-5 seconds.
    Server saves to DB, checks arrival, and broadcasts to customer.

    data = { job_id, worker_id, latitude, longitude }
    """
    job_id = data.get('job_id')
    worker_id = data.get('worker_id')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not all([job_id, worker_id, latitude, longitude]):
        emit('error', {'message': 'Missing required fields'})
        return

    # Save to database
    tracking = JobTracking(
        job_id=job_id,
        worker_id=worker_id,
        latitude=latitude,
        longitude=longitude
    )
    db.session.add(tracking)
    db.session.commit()

    # Check arrival
    arrived, distance = check_arrival(job_id, latitude, longitude)
    payload = {
        'latitude': latitude,
        'longitude': longitude,
        'timestamp': datetime.utcnow().isoformat(),
        'distance_to_job': distance
    }

    # Alert customer if worker arrived within 10 meters
    if arrived:
        emit('worker_arrived', {
            'message': 'Your worker has arrived!',
            'distance': distance
        }, room=f'job_{job_id}')

    emit('location_update', payload, room=f'job_{job_id}')


@socketio.on('disconnect')
def handle_disconnect():
    pass
