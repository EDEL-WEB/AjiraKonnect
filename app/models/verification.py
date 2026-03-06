from app import db
from datetime import datetime, timedelta
import uuid

class OTPVerification(db.Model):
    __tablename__ = 'otp_verifications'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    purpose = db.Column(db.String(20), default='registration')
    is_verified = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.utcnow() + timedelta(minutes=10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class WorkerVerification(db.Model):
    __tablename__ = 'worker_verifications'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_id = db.Column(db.String(36), db.ForeignKey('workers.id'), unique=True, nullable=False)
    
    # ID Verification
    national_id_number = db.Column(db.String(50))
    national_id_front_url = db.Column(db.Text)
    national_id_back_url = db.Column(db.Text)
    id_verification_score = db.Column(db.Integer, default=0)
    id_verified = db.Column(db.Boolean, default=False)
    
    # Phone Verification
    phone_verified = db.Column(db.Boolean, default=False)
    phone_verification_date = db.Column(db.DateTime)
    
    # Face Verification
    selfie_url = db.Column(db.Text)
    face_match_score = db.Column(db.Float, default=0.0)
    face_verified = db.Column(db.Boolean, default=False)
    
    # Skill Verification
    skill_documents_url = db.Column(db.ARRAY(db.Text))
    skill_verification_score = db.Column(db.Integer, default=0)
    skill_verified = db.Column(db.Boolean, default=False)
    
    # Overall
    overall_score = db.Column(db.Integer, default=0)
    auto_approved = db.Column(db.Boolean, default=False)
    manual_review_required = db.Column(db.Boolean, default=False)
    
    # Flagging
    flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.Text)
    
    # Admin Review
    reviewed_by = db.Column(db.String(36))
    reviewed_at = db.Column(db.DateTime)
    admin_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LoginAttempt(db.Model):
    __tablename__ = 'login_attempts'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    email = db.Column(db.String(120), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    success = db.Column(db.Boolean, default=False)
    failure_reason = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
