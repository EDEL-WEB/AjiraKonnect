from app import db
from app.models import Notification, UserPresence, User
from datetime import datetime, timedelta

class NotificationService:
    
    @staticmethod
    def is_user_online(user_id):
        """Check if user is currently online (active in last 5 minutes)"""
        presence = UserPresence.query.filter_by(user_id=user_id).first()
        
        if not presence or not presence.is_online:
            return False
        
        # Consider online if last heartbeat within 5 minutes
        threshold = datetime.utcnow() - timedelta(minutes=5)
        return presence.last_heartbeat > threshold
    
    @staticmethod
    def update_presence(user_id, is_online=True, device_id=None, device_type=None, ip_address=None):
        """Update user's online presence"""
        presence = UserPresence.query.filter_by(user_id=user_id).first()
        
        if not presence:
            presence = UserPresence(user_id=user_id)
            db.session.add(presence)
        
        presence.is_online = is_online
        presence.last_heartbeat = datetime.utcnow()
        
        if is_online:
            presence.last_seen = datetime.utcnow()
        
        if device_id:
            presence.device_id = device_id
        if device_type:
            presence.device_type = device_type
        if ip_address:
            presence.ip_address = ip_address
        
        db.session.commit()
        return presence
    
    @staticmethod
    def send_notification(user_id, message, title=None, job_id=None, priority='normal'):
        """
        Smart notification: Send push if online, SMS if offline
        
        Logic:
        - Check if user is online
        - If online: Send push notification
        - If offline: Queue SMS notification
        """
        user = User.query.get_or_404(user_id)
        is_online = NotificationService.is_user_online(user_id)
        
        # Determine notification type based on online status
        notification_type = 'push' if is_online else 'sms'
        
        notification = Notification(
            user_id=user_id,
            job_id=job_id,
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            status='pending'
        )
        
        db.session.add(notification)
        db.session.commit()
        
        if notification_type == 'sms':
            NotificationService._send_sms_notification(notification, user)
        else:
            NotificationService._send_push_notification(notification)

        return notification
    
    @staticmethod
    def _send_push_notification(notification):
        """Emit real-time push via WebSocket to the online worker/customer."""
        try:
            from app import socketio
            socketio.emit(
                'notification',
                {
                    'id':       notification.id,
                    'title':    notification.title,
                    'message':  notification.message,
                    'job_id':   notification.job_id,
                    'priority': notification.priority,
                },
                room=notification.user_id   # client must join room = their user_id on connect
            )
            notification.status = 'sent'
            notification.sent_at = datetime.utcnow()
            db.session.commit()
        except Exception as e:
            notification.status = 'failed'
            notification.error_message = str(e)
            db.session.commit()

    @staticmethod
    def _send_sms_notification(notification, user):
        """Send SMS fallback via Africa's Talking when worker is offline."""
        try:
            from app.services.sms_service import SMSService
            success = SMSService().send_sms(user.phone, notification.message)

            if success:
                notification.status = 'sent'
                notification.sent_at = datetime.utcnow()
            else:
                notification.status = 'failed'
                notification.retry_count += 1

            db.session.commit()
        except Exception as e:
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.retry_count += 1
            db.session.commit()
    
    @staticmethod
    def notify_job_created(job):
        """Notify worker about new job in their area/category"""
        from app.models import Worker, WorkerSkill
        
        # Find workers with matching skills
        workers = Worker.query.join(WorkerSkill).filter(
            WorkerSkill.category_id == job.category_id,
            Worker.verification_status == 'verified',
            Worker.availability == True
        ).all()
        
        for worker in workers[:5]:  # Notify top 5 workers
            message = f"New job available: {job.title} in {job.location}. Budget: KES {job.budget}"
            NotificationService.send_notification(
                worker.user_id,
                message,
                title="New Job Available",
                job_id=job.id,
                priority='high'
            )
    
    @staticmethod
    def notify_job_accepted(job):
        """Notify customer that worker accepted their job"""
        message = f"Your job '{job.title}' has been accepted by a worker!"
        NotificationService.send_notification(
            job.customer_id,
            message,
            title="Job Accepted",
            job_id=job.id,
            priority='high'
        )
    
    @staticmethod
    def notify_job_completed(job):
        """Notify customer that job is completed"""
        message = f"Job '{job.title}' has been marked as completed. Please review and approve."
        NotificationService.send_notification(
            job.customer_id,
            message,
            title="Job Completed",
            job_id=job.id,
            priority='high'
        )
    
    @staticmethod
    def notify_payment_released(job, amount):
        """Notify worker that payment has been released"""
        message = f"Payment of KES {amount} released for job: {job.title}"
        NotificationService.send_notification(
            job.worker.user_id,
            message,
            title="Payment Received",
            job_id=job.id,
            priority='high'
        )
    
    @staticmethod
    def retry_failed_notifications():
        """Background task to retry failed notifications"""
        failed = Notification.query.filter(
            Notification.status == 'failed',
            Notification.retry_count < Notification.max_retries
        ).all()
        
        for notification in failed:
            user = User.query.get(notification.user_id)
            
            if notification.type == 'sms':
                NotificationService._send_sms_notification(notification, user)
    
    @staticmethod
    def get_pending_notifications(user_id):
        """Get all pending notifications for user"""
        return Notification.query.filter_by(
            user_id=user_id,
            status='pending'
        ).order_by(Notification.priority.desc(), Notification.created_at).all()
