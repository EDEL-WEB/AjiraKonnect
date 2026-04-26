import uuid
from datetime import datetime
from app import db

class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    worker_id = db.Column(db.String(36), db.ForeignKey('workers.id', ondelete='SET NULL'), index=True)
    category_id = db.Column(db.String(36), db.ForeignKey('categories.id', ondelete='SET NULL'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    job_latitude = db.Column(db.Float)
    job_longitude = db.Column(db.Float)
    budget = db.Column(db.Numeric(10, 2), nullable=True)
    proposed_rate = db.Column(db.Numeric(10, 2))
    rate_status = db.Column(db.Enum('pending_approval', 'approved', 'rejected', name='rate_statuses'), nullable=True)
    status = db.Column(db.Enum('pending', 'accepted', 'in_progress', 'completed', 'disputed', 'cancelled', name='job_statuses'), default='pending', index=True)
    scheduled_date = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    payment = db.relationship('Payment', backref='job', uselist=False, cascade='all, delete-orphan')
    review = db.relationship('Review', backref='job', uselist=False, cascade='all, delete-orphan')
