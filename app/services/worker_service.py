from app import db
from app.models import Worker, WorkerSkill, User

class WorkerService:
    @staticmethod
    def create_worker_profile(user_id, hourly_rate, location, bio, skills):
        user = User.query.get_or_404(user_id)
        if user.role != 'worker':
            raise ValueError('User must have worker role')
        
        if Worker.query.filter_by(user_id=user_id).first():
            raise ValueError('Worker profile already exists')
        
        worker = Worker(user_id=user_id, hourly_rate=hourly_rate, location=location, bio=bio)
        db.session.add(worker)
        db.session.flush()
        
        for skill in skills:
            worker_skill = WorkerSkill(worker_id=worker.id, category_id=skill['category_id'], 
                                      experience_years=skill.get('experience_years', 0))
            db.session.add(worker_skill)
        
        # Auto-create verification record
        from app.models.verification import WorkerVerification
        verification = WorkerVerification(worker_id=worker.id)
        db.session.add(verification)
        
        db.session.commit()
        return worker
    
    @staticmethod
    def search_workers(category_id=None, location=None, min_rating=None, available_only=True):
        query = Worker.query.filter_by(verification_status='verified')
        
        if available_only:
            query = query.filter_by(availability=True)
        
        if category_id:
            query = query.join(WorkerSkill).filter(WorkerSkill.category_id == category_id)
        
        if location:
            query = query.filter(Worker.location.ilike(f'%{location}%'))
        
        if min_rating:
            query = query.filter(Worker.rating >= min_rating)
        
        return query.all()
    
    @staticmethod
    def update_worker_rating(worker_id, new_rating):
        worker = Worker.query.get_or_404(worker_id)
        total = worker.total_reviews
        current_rating = float(worker.rating)
        
        worker.total_reviews = total + 1
        worker.rating = ((current_rating * total) + new_rating) / worker.total_reviews
        
        db.session.commit()
        return worker
