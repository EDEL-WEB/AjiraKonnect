import uuid
from datetime import datetime
from app import db

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    job_id = db.Column(db.String(36), db.ForeignKey('jobs.id', ondelete='CASCADE'), index=True)
    
    # Notification type: push, sms, ussd
    type = db.Column(db.Enum('push', 'sms', 'ussd', name='notification_types'), nullable=False)
    
    # Message content
    title = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    
    # Delivery status
    status = db.Column(db.Enum('pending', 'sent', 'delivered', 'failed', name='notification_statuses'), default='pending', index=True)
    
    # Priority: high, normal, low
    priority = db.Column(db.Enum('high', 'normal', 'low', name='notification_priorities'), default='normal')
    
    # Retry tracking
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=3)
    
    # Timestamps
    scheduled_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # External tracking
    external_id = db.Column(db.String(100))
    error_message = db.Column(db.Text)

class UserPresence(db.Model):
    __tablename__ = 'user_presence'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    
    # Online status
    is_online = db.Column(db.Boolean, default=False, index=True)
    
    # Last activity
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Device info
    device_id = db.Column(db.String(100))
    device_type = db.Column(db.String(50))
    app_version = db.Column(db.String(20))
    
    # Connection info
    ip_address = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
