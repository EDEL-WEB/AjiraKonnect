import uuid
from datetime import datetime
from app import db
import bcrypt

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    phone_verified = db.Column(db.Boolean, default=False)
    role = db.Column(db.Enum('customer', 'worker', 'admin', name='user_roles'), nullable=False, default='customer')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    worker_profile = db.relationship('Worker', backref='user', uselist=False, cascade='all, delete-orphan')
    wallet = db.relationship('Wallet', backref='user', uselist=False, cascade='all, delete-orphan')
    jobs_posted = db.relationship('Job', foreign_keys='Job.customer_id', backref='customer', lazy='dynamic')
    reviews_given = db.relationship('Review', foreign_keys='Review.customer_id', backref='customer', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
