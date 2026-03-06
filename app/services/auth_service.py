from app import db
from app.models import User, Wallet, OTPVerification, LoginAttempt
from flask_jwt_extended import create_access_token
from datetime import datetime, timedelta
import random
import string

class AuthService:
    @staticmethod
    def register_user(email, password, full_name, phone, role='customer'):
        if User.query.filter_by(email=email).first():
            raise ValueError('Email already registered')
        
        user = User(email=email, full_name=full_name, phone=phone, role=role)
        user.set_password(password)
        user.is_active = False
        
        db.session.add(user)
        db.session.flush()
        
        wallet = Wallet(user_id=user.id)
        db.session.add(wallet)
        
        otp_code = AuthService._generate_otp()
        AuthService._create_otp(user.id, phone, otp_code, 'registration')
        
        from app.services.sms_service import SMSService
        sms = SMSService()
        sms.send_otp(phone, otp_code)
        
        db.session.commit()
        return user
    
    @staticmethod
    def verify_otp(user_id, otp_code):
        otp = OTPVerification.query.filter_by(
            user_id=user_id,
            otp_code=otp_code,
            is_verified=False
        ).filter(OTPVerification.expires_at > datetime.utcnow()).first()
        
        if not otp:
            raise ValueError('Invalid or expired OTP')
        
        otp.is_verified = True
        user = User.query.get(user_id)
        user.phone_verified = True
        
        if user.role == 'customer':
            user.is_active = True
        
        db.session.commit()
        return True
    
    @staticmethod
    def login_user(email, password, ip_address=None, user_agent=None):
        user = User.query.filter_by(email=email).first()
        
        attempt = LoginAttempt(
            user_id=user.id if user else None,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if not user or not user.check_password(password):
            attempt.success = False
            attempt.failure_reason = 'Invalid credentials'
            db.session.add(attempt)
            db.session.commit()
            raise ValueError('Invalid credentials')
        
        if not user.is_active:
            attempt.success = False
            if user.role == 'customer':
                attempt.failure_reason = 'Phone not verified'
                db.session.add(attempt)
                db.session.commit()
                raise ValueError('Please verify your phone number first.')
            elif user.role == 'worker':
                attempt.failure_reason = 'Worker verification pending'
                db.session.add(attempt)
                db.session.commit()
                raise ValueError('Your worker verification is pending. Please complete verification or wait for admin approval.')
            else:
                attempt.failure_reason = 'Account not active'
                db.session.add(attempt)
                db.session.commit()
                raise ValueError('Account is not active.')
        
        recent_failures = LoginAttempt.query.filter(
            LoginAttempt.email == email,
            LoginAttempt.success == False,
            LoginAttempt.created_at > datetime.utcnow() - timedelta(minutes=15)
        ).count()
        
        if recent_failures >= 5:
            attempt.success = False
            attempt.failure_reason = 'Too many failed attempts'
            db.session.add(attempt)
            db.session.commit()
            raise ValueError('Account temporarily locked. Try again later.')
        
        if user.role == 'customer':
            otp_code = AuthService._generate_otp()
            AuthService._create_otp(user.id, user.phone, otp_code, 'login')
            
            from app.services.sms_service import SMSService
            sms = SMSService()
            sms.send_otp(user.phone, otp_code)
            
            attempt.success = False
            attempt.failure_reason = '2FA required'
            db.session.add(attempt)
            db.session.commit()
            
            return {'requires_2fa': True, 'user_id': user.id}
        
        attempt.success = True
        db.session.add(attempt)
        db.session.commit()
        
        token = create_access_token(identity=user.id, additional_claims={'role': user.role})
        return {'token': token, 'user': user, 'requires_2fa': False}
    
    @staticmethod
    def verify_login_otp(user_id, otp_code):
        otp = OTPVerification.query.filter_by(
            user_id=user_id,
            otp_code=otp_code,
            purpose='login',
            is_verified=False
        ).filter(OTPVerification.expires_at > datetime.utcnow()).first()
        
        if not otp:
            raise ValueError('Invalid or expired OTP')
        
        otp.is_verified = True
        user = User.query.get(user_id)
        
        db.session.commit()
        
        token = create_access_token(identity=user.id, additional_claims={'role': user.role})
        return token, user
    
    @staticmethod
    def _generate_otp():
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def _create_otp(user_id, phone, otp_code, purpose):
        otp = OTPVerification(
            user_id=user_id,
            phone=phone,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(otp)
        return otp
    
    @staticmethod
    def create_admin(email, password, full_name, phone):
        if User.query.filter_by(email=email).first():
            raise ValueError('Email already exists')
        
        user = User(email=email, full_name=full_name, phone=phone, role='admin')
        user.set_password(password)
        user.is_active = True
        user.phone_verified = True
        
        db.session.add(user)
        db.session.flush()
        
        wallet = Wallet(user_id=user.id)
        db.session.add(wallet)
        
        db.session.commit()
        return user
