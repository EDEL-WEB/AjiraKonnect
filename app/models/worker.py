import uuid
from datetime import datetime
from app import db

class Worker(db.Model):
    __tablename__ = 'workers'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    hourly_rate = db.Column(db.Numeric(10, 2), nullable=False)
    location = db.Column(db.String(200), nullable=False, index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    bio = db.Column(db.Text)
    availability = db.Column(db.Boolean, default=True)
    verification_status = db.Column(db.Enum('pending', 'verified', 'rejected', name='verification_statuses'), default='pending')
    flagged_for_review = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Numeric(3, 2), default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    total_jobs_completed = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    skills = db.relationship('WorkerSkill', backref='worker', cascade='all, delete-orphan')
    jobs = db.relationship('Job', foreign_keys='Job.worker_id', backref='worker', lazy='dynamic')
    reviews = db.relationship('Review', foreign_keys='Review.worker_id', backref='worker', lazy='dynamic')

class WorkerSkill(db.Model):
    __tablename__ = 'worker_skills'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_id = db.Column(db.String(36), db.ForeignKey('workers.id', ondelete='CASCADE'), nullable=False)
    category_id = db.Column(db.String(36), db.ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    experience_years = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
