from app import db
from app.models import Job, Payment, Worker
from flask import current_app

class JobService:
    @staticmethod
    def create_job(customer_id, category_id, title, description, location, budget, scheduled_date=None):
        job = Job(customer_id=customer_id, category_id=category_id, title=title,
                 description=description, location=location, budget=budget, scheduled_date=scheduled_date)
        db.session.add(job)
        db.session.commit()

        from app.services.notification_service import NotificationService
        NotificationService.notify_job_created(job)

        return job
    
    @staticmethod
    def accept_job(job_id, worker_id):
        job = Job.query.get_or_404(job_id)
        if job.status != 'pending':
            raise ValueError('Job is not available')
        
        job.worker_id = worker_id
        job.status = 'accepted'
        
        commission_rate = current_app.config['COMMISSION_RATE']
        commission = float(job.budget) * commission_rate
        worker_payout = float(job.budget) - commission
        
        payment = Payment(job_id=job.id, amount=job.budget, commission=commission, 
                         worker_payout=worker_payout, status='held')
        db.session.add(payment)
        
        db.session.commit()

        from app.services.notification_service import NotificationService
        NotificationService.notify_job_accepted(job)

        return job
    
    @staticmethod
    def update_job_status(job_id, new_status):
        job = Job.query.get_or_404(job_id)
        
        valid_transitions = {
            'pending': ['accepted', 'cancelled'],
            'accepted': ['in_progress', 'cancelled'],
            'in_progress': ['completed', 'disputed', 'cancelled'],
            'disputed': ['completed', 'cancelled'],
        }
        
        if new_status not in valid_transitions.get(job.status, []):
            raise ValueError(f'Cannot transition from {job.status} to {new_status}')
        
        job.status = new_status
        
        if new_status == 'completed':
            from datetime import datetime
            job.completed_at = datetime.utcnow()
            
            worker = Worker.query.get(job.worker_id)
            worker.total_jobs_completed += 1
        
        db.session.commit()
        return job
