import uuid
from datetime import datetime
from app import db

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = db.Column(db.String(36), db.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False, unique=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    commission = db.Column(db.Numeric(10, 2), nullable=False)
    worker_payout = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum('pre_authorized', 'held', 'released', 'refunded', 'disputed', name='payment_statuses'), default='pre_authorized', index=True)
    dispute_reason = db.Column(db.Text)
    resolution_note = db.Column(db.Text)
    paid_at = db.Column(db.DateTime)
    released_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    transactions = db.relationship('Transaction', backref='payment', cascade='all, delete-orphan')

class Wallet(db.Model):
    __tablename__ = 'wallets'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    balance = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    transactions = db.relationship('Transaction', backref='wallet', cascade='all, delete-orphan')

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_id = db.Column(db.String(36), db.ForeignKey('wallets.id', ondelete='CASCADE'), nullable=False, index=True)
    payment_id = db.Column(db.String(36), db.ForeignKey('payments.id', ondelete='SET NULL'))
    type = db.Column(db.Enum('credit', 'debit', name='transaction_types'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255))
    balance_after = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
