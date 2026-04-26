from app import db
from app.models import Worker, WorkerSkill, User
import math


def haversine_km(lat1, lon1, lat2, lon2):
    """Return distance in km between two coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


class WorkerService:
    @staticmethod
    def create_worker_profile(user_id, hourly_rate, location, bio, skills, latitude=None, longitude=None):
        user = User.query.get_or_404(user_id)
        if user.role != 'worker':
            raise ValueError('User must have worker role')
        
        if Worker.query.filter_by(user_id=user_id).first():
            raise ValueError('Worker profile already exists')
        
        worker = Worker(
            user_id=user_id, hourly_rate=hourly_rate, location=location,
            bio=bio, latitude=latitude, longitude=longitude
        )
        db.session.add(worker)
        db.session.flush()
        
        # Skip skills for now - can be added later
        # for skill in skills:
        #     worker_skill = WorkerSkill(worker_id=worker.id, category_id=skill['category_id'], 
        #                               experience_years=skill.get('experience_years', 0))
        #     db.session.add(worker_skill)
        
        # Auto-create verification record
        from app.models.verification import WorkerVerification
        verification = WorkerVerification(worker_id=worker.id)
        db.session.add(verification)
        
        db.session.commit()
        return worker
    
    @staticmethod
    def get_recommended_workers(job_description, location=None, latitude=None, longitude=None,
                                max_hourly_rate=None, radius_km=20, limit=10):
        """
        Score workers by distance (40%), rating (30%), and bio relevance (30%).
        Falls back to text location filter when coordinates are unavailable.
        """
        query = Worker.query.filter_by(verification_status='verified', availability=True)

        if max_hourly_rate:
            query = query.filter(Worker.hourly_rate <= max_hourly_rate)

        # Broad location pre-filter when no coordinates
        if not (latitude and longitude) and location:
            query = query.filter(Worker.location.ilike(f'%{location}%'))

        candidates = query.all()
        job_keywords = set(job_description.lower().split()) if job_description else set()
        scored = []

        for worker in candidates:
            # Distance score (40%) — penalise workers far away
            if latitude and longitude and worker.latitude and worker.longitude:
                dist = haversine_km(latitude, longitude, worker.latitude, worker.longitude)
                if dist > radius_km:
                    continue  # outside radius, skip
                distance_score = max(0, 1 - dist / radius_km) * 0.4
            else:
                distance_score = 0.2  # neutral when no coords

            # Rating score (30%)
            rating_score = (float(worker.rating or 0) / 5.0) * 0.3

            # Bio relevance score (30%)
            text_score = 0
            if worker.bio and job_keywords:
                bio_words = set(worker.bio.lower().split())
                intersection = len(job_keywords & bio_words)
                union = len(job_keywords | bio_words)
                text_score = (intersection / union if union > 0 else 0) * 0.3

            scored.append((distance_score + rating_score + text_score, worker))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [w for _, w in scored[:limit]]

    @staticmethod
    def search_workers(category_id=None, location=None, latitude=None, longitude=None,
                       min_rating=None, radius_km=20, available_only=True):
        query = Worker.query.filter_by(verification_status='verified')

        if available_only:
            query = query.filter_by(availability=True)
        if category_id:
            query = query.join(WorkerSkill).filter(WorkerSkill.category_id == category_id)
        if min_rating:
            query = query.filter(Worker.rating >= min_rating)

        workers = query.all()

        # Filter by radius when coordinates provided, else fall back to text
        if latitude and longitude:
            workers = [
                w for w in workers
                if w.latitude and w.longitude
                and haversine_km(latitude, longitude, w.latitude, w.longitude) <= radius_km
            ]
            workers.sort(key=lambda w: haversine_km(latitude, longitude, w.latitude, w.longitude))
        elif location:
            workers = [w for w in workers if location.lower() in w.location.lower()]

        return workers
    
    @staticmethod
    def update_worker_rating(worker_id, new_rating):
        worker = Worker.query.get_or_404(worker_id)
        total = worker.total_reviews
        current_rating = float(worker.rating)
        
        worker.total_reviews = total + 1
        worker.rating = ((current_rating * total) + new_rating) / worker.total_reviews
        
        db.session.commit()
        return worker
