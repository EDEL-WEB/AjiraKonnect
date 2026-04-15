from app import db
from app.models.offline import SMSLog
from app.services.africastalking_service import at_service

class SMSService:
    def send_sms(self, phone, message):
        try:
            result = at_service.send_sms(phone, message)
            log = SMSLog(
                phone=phone,
                message=message,
                direction='outbound',
                status='sent',
                external_id=result.get('message_id')
            )
            db.session.add(log)
            db.session.commit()
            return True
        except Exception as e:
            log = SMSLog(phone=phone, message=message, direction='outbound', status='failed')
            db.session.add(log)
            db.session.commit()
            return False
    
    def send_job_notification(self, phone, job_title, job_id):
        message = f"New job: {job_title}. Reply YES {job_id} to accept or NO {job_id} to decline."
        return self.send_sms(phone, message)
    
    def send_otp(self, phone, otp_code):
        message = f"Your KaziConnect code: {otp_code}. Valid 10 mins."
        return self.send_sms(phone, message)
    
    def send_job_status_update(self, phone, job_title, status):
        message = f"Job '{job_title}' status: {status.upper()}"
        return self.send_sms(phone, message)
    
    def send_payment_notification(self, phone, amount, job_title):
        message = f"Payment KES {amount} released for: {job_title}"
        return self.send_sms(phone, message)
    
    def handle_incoming_sms(self, phone, text, message_id):
        log = SMSLog(
            phone=phone,
            message=text,
            direction='inbound',
            status='received',
            external_id=message_id
        )
        db.session.add(log)
        db.session.commit()
        
        text = text.strip().upper()
        
        if text.startswith('YES '):
            job_id = text.split()[1]
            return {'action': 'accept_job', 'job_id': job_id, 'phone': phone}
        elif text.startswith('NO '):
            job_id = text.split()[1]
            return {'action': 'decline_job', 'job_id': job_id, 'phone': phone}
        
        return {'action': 'unknown', 'phone': phone}
