from app import db
from datetime import datetime
import uuid

class JobTracking(db.Model):
    __tablename__ = 'job_tracking'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = db.Column(db.String(36), db.ForeignKey('jobs.id'), nullable=False)
    worker_id = db.Column(db.String(36), db.ForeignKey('workers.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        db.Index('idx_job_tracking_job_id', 'job_id'),
    )
