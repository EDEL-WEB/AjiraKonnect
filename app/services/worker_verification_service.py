from app import db
from app.models import Worker, WorkerVerification, OTPVerification, User
from datetime import datetime, timedelta
import random
import string

class WorkerVerificationService:
    
    @staticmethod
    def initiate_verification(worker_id):
        verification = WorkerVerification.query.filter_by(worker_id=worker_id).first()
        if not verification:
            verification = WorkerVerification(worker_id=worker_id)
            db.session.add(verification)
            db.session.commit()
        return verification
    
    @staticmethod
    def upload_national_id(worker_id, national_id_number, front_url, back_url):
        verification = WorkerVerification.query.filter_by(worker_id=worker_id).first_or_404()
        
        existing = WorkerVerification.query.filter(
            WorkerVerification.national_id_number == national_id_number,
            WorkerVerification.worker_id != worker_id
        ).first()
        
        if existing:
            verification.flagged = True
            verification.flag_reason = 'Duplicate national ID detected'
            db.session.commit()
            raise ValueError('National ID already registered')
        
        verification.national_id_number = national_id_number
        verification.national_id_front_url = front_url
        verification.national_id_back_url = back_url
        verification.id_verification_score = 25
        verification.id_verified = True
        
        WorkerVerificationService._calculate_overall_score(verification)
        db.session.commit()
        return verification
    
    @staticmethod
    def verify_phone(worker_id, otp_code):
        worker = Worker.query.get_or_404(worker_id)
        user = User.query.get(worker.user_id)
        
        otp = OTPVerification.query.filter_by(
            user_id=user.id,
            otp_code=otp_code,
            purpose='phone_verification',
            is_verified=False
        ).filter(OTPVerification.expires_at > datetime.utcnow()).first()
        
        if not otp:
            raise ValueError('Invalid or expired OTP')
        
        otp.is_verified = True
        user.phone_verified = True
        
        verification = WorkerVerification.query.filter_by(worker_id=worker_id).first_or_404()
        verification.phone_verified = True
        verification.phone_verification_date = datetime.utcnow()
        
        WorkerVerificationService._calculate_overall_score(verification)
        db.session.commit()
        return verification
    
    @staticmethod
    def upload_selfie(worker_id, selfie_url):
        verification = WorkerVerification.query.filter_by(worker_id=worker_id).first_or_404()
        
        if not verification.national_id_front_url:
            raise ValueError('Please upload national ID first')
        
        verification.selfie_url = selfie_url
        face_match_score = random.uniform(0.75, 0.95)
        verification.face_match_score = face_match_score
        
        if face_match_score >= 0.80:
            verification.face_verified = True
        elif face_match_score < 0.60:
            verification.flagged = True
            verification.flag_reason = 'Low face match score'
        
        WorkerVerificationService._calculate_overall_score(verification)
        db.session.commit()
        return verification
    
    @staticmethod
    def upload_skill_documents(worker_id, documents_urls):
        verification = WorkerVerification.query.filter_by(worker_id=worker_id).first_or_404()
        
        verification.skill_documents_url = documents_urls
        
        num_docs = len(documents_urls) if documents_urls else 0
        if num_docs >= 3:
            verification.skill_verification_score = 25
        elif num_docs >= 1:
            verification.skill_verification_score = 15
        else:
            verification.skill_verification_score = 0
        
        verification.skill_verified = True
        
        WorkerVerificationService._calculate_overall_score(verification)
        db.session.commit()
        return verification
    
    @staticmethod
    def _calculate_overall_score(verification):
        score = 0
        
        if verification.id_verified:
            score += verification.id_verification_score
        
        if verification.phone_verified:
            score += 20
        
        if verification.face_verified:
            score += int(verification.face_match_score * 30)
        
        if verification.skill_verified and verification.skill_verification_score > 0:
            score += verification.skill_verification_score
        
        verification.overall_score = score
        
        if verification.flagged:
            verification.manual_review_required = True
            verification.auto_approved = False
        elif score >= 60:
            verification.auto_approved = True
            verification.manual_review_required = False
            WorkerVerificationService._auto_approve_worker(verification)
        elif score >= 45:
            verification.manual_review_required = True
            verification.auto_approved = False
        else:
            verification.flagged = True
            verification.flag_reason = f'Low verification score: {score}'
            verification.manual_review_required = True
    
    @staticmethod
    def _auto_approve_worker(verification):
        """Auto-approve worker and activate their account"""
        worker = Worker.query.get(verification.worker_id)
        worker.verification_status = 'verified'
        
        # Activate user account so they can login
        user = User.query.get(worker.user_id)
        user.is_active = True
        
        # Send notification
        from app.services.notification_service import NotificationService
        NotificationService.send_notification(
            user.id,
            "Congratulations! Your worker account has been verified. You can now start accepting jobs.",
            title="Account Verified",
            priority='high'
        )
    
    @staticmethod
    def admin_review(verification_id, admin_id, approved, notes):
        verification = WorkerVerification.query.get_or_404(verification_id)
        worker = Worker.query.get(verification.worker_id)
        user = User.query.get(worker.user_id)
        
        verification.reviewed_by = admin_id
        verification.reviewed_at = datetime.utcnow()
        verification.admin_notes = notes
        
        if approved:
            worker.verification_status = 'verified'
            verification.manual_review_required = False
            verification.flagged = False
            
            # Activate user account
            user.is_active = True
            
            # Send approval notification
            from app.services.notification_service import NotificationService
            NotificationService.send_notification(
                user.id,
                "Your worker account has been approved by admin. You can now login and start accepting jobs.",
                title="Account Approved",
                priority='high'
            )
        else:
            worker.verification_status = 'rejected'
            verification.flagged = True
            
            # Send rejection notification
            from app.services.notification_service import NotificationService
            NotificationService.send_notification(
                user.id,
                f"Your worker verification was not approved. Reason: {notes}",
                title="Verification Rejected",
                priority='high'
            )
        
        db.session.commit()
        return verification
    
    @staticmethod
    def get_pending_reviews():
        return WorkerVerification.query.filter_by(
            manual_review_required=True,
            reviewed_by=None
        ).all()
    
    @staticmethod
    def get_flagged_verifications():
        return WorkerVerification.query.filter_by(flagged=True).all()
