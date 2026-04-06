from app import db
from app.models import User, Wallet, OTPVerification, LoginAttempt
from flask_jwt_extended import create_access_token
from datetime import datetime, timedelta
import random
import string


class AuthService:

    # -----------------------------
    # USER REGISTRATION
    # -----------------------------
    @staticmethod
    def register_user(email, password, full_name, phone, role='customer'):

        if User.query.filter_by(email=email).first():
            raise ValueError('Email already registered')

        user = User(
            email=email,
            full_name=full_name,
            phone=phone,
            role=role
        )

        user.set_password(password)
        user.is_active = False

        db.session.add(user)
        db.session.flush()

        wallet = Wallet(user_id=user.id)
        db.session.add(wallet)

        # generate registration OTP
        otp_code = AuthService._generate_otp()
        AuthService._create_otp(user.id, phone, otp_code, 'registration')

        from app.services.sms_service import SMSService
        sms = SMSService()
        sms.send_otp(phone, otp_code)

        db.session.commit()

        return user


    # -----------------------------
    # VERIFY REGISTRATION OTP
    # -----------------------------
    @staticmethod
    def verify_otp(user_id, otp_code):

        otp = OTPVerification.query.filter_by(
            user_id=user_id,
            otp_code=otp_code,
            is_verified=False
        ).filter(
            OTPVerification.expires_at > datetime.utcnow()
        ).first()

        if not otp:
            raise ValueError('Invalid or expired OTP')

        otp.is_verified = True

        user = User.query.get(user_id)
        user.phone_verified = True

        if user.role == "customer":
            user.is_active = True

        db.session.commit()

        return True


    # -----------------------------
    # LOGIN USER
    # -----------------------------
    @staticmethod
    def login_user(email, password, ip_address=None, user_agent=None):

        user = User.query.filter_by(email=email).first()

        attempt = LoginAttempt(
            user_id=user.id if user else None,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # -----------------------------
        # INVALID LOGIN
        # -----------------------------
        if not user or not user.check_password(password):

            attempt.success = False
            attempt.failure_reason = "Invalid credentials"

            db.session.add(attempt)
            db.session.commit()

            raise ValueError("Invalid credentials")

        # -----------------------------
        # ACCOUNT ACTIVE CHECK
        # -----------------------------
        if not user.is_active:

            attempt.success = False

            if user.role == "customer":
                attempt.failure_reason = "Phone not verified"

            elif user.role == "worker":
                attempt.failure_reason = "Worker verification pending"

            else:
                attempt.failure_reason = "Account inactive"

            db.session.add(attempt)
            db.session.commit()

            raise ValueError("Account not active")

        # -----------------------------
        # FAILED ATTEMPT PROTECTION
        # -----------------------------
        recent_failures = LoginAttempt.query.filter(
            LoginAttempt.email == email,
            LoginAttempt.success == False,
            LoginAttempt.created_at >
            datetime.utcnow() - timedelta(minutes=15)
        ).count()

        if recent_failures >= 5:

            attempt.success = False
            attempt.failure_reason = "Too many failed attempts"

            db.session.add(attempt)
            db.session.commit()

            raise ValueError("Account locked. Try later.")


        # -----------------------------
        # DEVICE / IP CHECK
        # -----------------------------
        requires_2fa = False

        last_login = LoginAttempt.query.filter_by(
            user_id=user.id,
            success=True
        ).order_by(
            LoginAttempt.created_at.desc()
        ).first()

        if last_login:

            if last_login.ip_address != ip_address:
                requires_2fa = True

            if last_login.user_agent != user_agent:
                requires_2fa = True


        # -----------------------------
        # SUSPICIOUS LOGIN DETECTION
        # -----------------------------
        suspicious_attempts = LoginAttempt.query.filter(
            LoginAttempt.email == email,
            LoginAttempt.success == False,
            LoginAttempt.created_at >
            datetime.utcnow() - timedelta(minutes=5)
        ).count()

        if suspicious_attempts >= 3:
            requires_2fa = True


        # -----------------------------
        # REQUIRE OTP ONLY IF SUSPICIOUS
        # -----------------------------
        if requires_2fa:

            otp_code = AuthService._generate_otp()

            AuthService._create_otp(
                user.id,
                user.phone,
                otp_code,
                "login"
            )

            from app.services.sms_service import SMSService
            sms = SMSService()
            sms.send_otp(user.phone, otp_code)

            attempt.success = False
            attempt.failure_reason = "2FA required"

            db.session.add(attempt)
            db.session.commit()

            return {
                "requires_2fa": True,
                "user_id": user.id
            }


        # -----------------------------
        # SUCCESSFUL LOGIN
        # -----------------------------
        attempt.success = True

        db.session.add(attempt)
        db.session.commit()

        token = create_access_token(
            identity=user.id,
            additional_claims={"role": user.role}
        )

        return {
            "token": token,
            "user": user,
            "requires_2fa": False
        }


    # -----------------------------
    # VERIFY LOGIN OTP
    # -----------------------------
    @staticmethod
    def verify_login_otp(user_id, otp_code):

        otp = OTPVerification.query.filter_by(
            user_id=user_id,
            otp_code=otp_code,
            purpose="login",
            is_verified=False
        ).filter(
            OTPVerification.expires_at > datetime.utcnow()
        ).first()

        if not otp:
            raise ValueError("Invalid or expired OTP")

        otp.is_verified = True

        user = User.query.get(user_id)

        db.session.commit()

        token = create_access_token(
            identity=user.id,
            additional_claims={"role": user.role}
        )

        return token, user


    # -----------------------------
    # GENERATE OTP
    # -----------------------------
    @staticmethod
    def _generate_otp():

        return ''.join(
            random.choices(string.digits, k=6)
        )


    # -----------------------------
    # CREATE OTP RECORD
    # -----------------------------
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


    # -----------------------------
    # CREATE ADMIN
    # -----------------------------
    @staticmethod
    def create_admin(email, password, full_name, phone):

        if User.query.filter_by(email=email).first():
            raise ValueError("Email already exists")

        user = User(
            email=email,
            full_name=full_name,
            phone=phone,
            role="admin"
        )

        user.set_password(password)

        user.is_active = True
        user.phone_verified = True

        db.session.add(user)
        db.session.flush()

        wallet = Wallet(user_id=user.id)
        db.session.add(wallet)

        db.session.commit()

        return user