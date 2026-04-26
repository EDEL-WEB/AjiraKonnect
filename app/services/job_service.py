from app import db
from app.models import Job, Payment, Worker
from datetime import datetime, timedelta
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
    def accept_job(job_id, worker_id, proposed_rate):
        job = Job.query.get_or_404(job_id)
        if job.status != 'pending':
            raise ValueError('Job is not available')

        try:
            proposed_rate = float(proposed_rate)
            if proposed_rate <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            raise ValueError('Invalid proposed rate')

        job.worker_id     = worker_id
        job.status        = 'accepted'
        job.proposed_rate = proposed_rate
        job.rate_status   = 'pending_approval'
        db.session.commit()

        from app.services.notification_service import NotificationService
        NotificationService.notify_rate_proposed(job)

        return job

    @staticmethod
    def approve_rate(job_id, customer_id, approved):
        job = Job.query.get_or_404(job_id)

        if job.customer_id != customer_id:
            raise ValueError('Only the job customer can approve the rate')
        if job.rate_status != 'pending_approval':
            raise ValueError('No pending rate to approve')

        if approved:
            job.rate_status = 'approved'
            job.budget      = job.proposed_rate
            db.session.commit()
            # Now hold funds in escrow
            from app.services.escrow_service import EscrowService
            EscrowService.pre_authorize(job_id, customer_id)
            EscrowService.hold_payment(job_id)
            from app.services.notification_service import NotificationService
            NotificationService.notify_rate_approved(job)
        else:
            job.rate_status = 'rejected'
            job.status      = 'cancelled'
            db.session.commit()
            from app.services.notification_service import NotificationService
            NotificationService.notify_rate_rejected(job)

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
        
        # ── BLOCK COMPLETION WITHOUT ESCROW PAYMENT ──────────────────────────
        if new_status == 'completed':
            if job.rate_status != 'approved':
                raise ValueError('Customer must approve the proposed rate before job can be completed.')
            payment = Payment.query.filter_by(job_id=job_id).first()
            if not payment or payment.status != 'held':
                raise ValueError('Payment must be held in escrow before completing this job.')
        
        job.status = new_status
        
        if new_status == 'completed':
            job.completed_at = datetime.utcnow()
            worker = Worker.query.get(job.worker_id)
            worker.total_jobs_completed += 1
            JobService._run_off_platform_detection(job.worker_id)
        
        db.session.commit()
        return job

    @staticmethod
    def _run_off_platform_detection(worker_id):
        """Detect workers with suspicious off-platform payment patterns"""
        # Count completed jobs in last 30 days
        since = datetime.utcnow() - timedelta(days=30)
        completed = Job.query.filter(
            Job.worker_id == worker_id,
            Job.status == 'completed',
            Job.completed_at >= since
        ).count()

        if completed < 3:
            return  # Not enough data

        # Count jobs paid through platform
        paid = db.session.query(Job).join(
            Payment, Payment.job_id == Job.id
        ).filter(
            Job.worker_id == worker_id,
            Job.status == 'completed',
            Job.completed_at >= since,
            Payment.status == 'released'
        ).count()

        payment_rate = paid / completed if completed > 0 else 0

        # Flag if less than 70% of completed jobs were paid through platform
        if payment_rate < 0.7:
            JobService._flag_worker(worker_id, completed, paid, payment_rate)

    @staticmethod
    def _flag_worker(worker_id, completed, paid, rate):
        worker = Worker.query.get(worker_id)
        if not worker:
            return

        worker.flagged_for_review = True
        db.session.commit()

        # Notify admin
        from app.models import User
        user = User.query.get(worker.user_id)
        from app.services.notification_service import NotificationService
        NotificationService.send_notification(
            user.id,
            f'Your account has been flagged: {completed} completed jobs but only '
            f'{paid} paid through KaziConnect ({int(rate*100)}%). '
            f'Off-platform payments violate our terms. Account may be suspended.',
            title='Account Flagged - Payment Policy Violation',
            priority='high'
        )
