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
    def get_recommended_workers(job_description, location=None, max_hourly_rate=None, limit=10):
        """
        Recommends workers based on a weighted score of Rating, Location, and Text Relevance.
        This is a 'Heuristic' model - the first step towards Machine Learning.
        """
        # 1. Fetch Candidates (Broad Filter)
        query = Worker.query.filter_by(verification_status='verified', availability=True)
        
        if location:
            # Strict filter for location, or use radius in future
            query = query.filter(Worker.location.ilike(f'%{location}%'))
        
        if max_hourly_rate:
            query = query.filter(Worker.hourly_rate <= max_hourly_rate)
            
        candidates = query.all()
        
        # 2. Score Candidates (The "Brain" of the recommendation)
        scored_workers = []
        job_keywords = set(job_description.lower().split()) if job_description else set()

        for worker in candidates:
            score = 0
            
            # Feature A: Social Proof (40% weight)
            # Normalize rating (0-5) to (0-1)
            rating_score = (float(worker.rating or 0) / 5.0) * 0.4
            score += rating_score
            
            # Feature B: Content Relevance (60% weight)
            # Simple Keyword Matching (Jaccard Similarity)
            if worker.bio and job_keywords:
                bio_words = set(worker.bio.lower().split())
                # Calculate overlap: intersection / union
                intersection = len(job_keywords.intersection(bio_words))
                union = len(job_keywords.union(bio_words))
                text_score = (intersection / union) if union > 0 else 0
                score += text_score * 0.6
            
            scored_workers.append((score, worker))
        
        # 3. Sort by Score (Highest First)
        scored_workers.sort(key=lambda x: x[0], reverse=True)
        
        return [item[1] for item in scored_workers[:limit]]

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
