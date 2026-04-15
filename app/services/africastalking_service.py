import os
import africastalking


class AfricasTalkingService:
    """
    Central Africa's Talking client.
    Lazy-initialized on first use so .env is loaded before credentials are read.
    """
    _initialized = False

    def _init(self):
        if self._initialized:
            return
        username = os.getenv('AFRICASTALKING_USERNAME', 'sandbox')
        api_key  = os.getenv('AFRICASTALKING_API_KEY')
        if not api_key:
            raise EnvironmentError('AFRICASTALKING_API_KEY is not set')
        africastalking.initialize(username, api_key)
        self.sms         = africastalking.SMS
        self.airtime     = africastalking.Airtime
        self.application = africastalking.Application
        self._initialized = True

    # ── Account ───────────────────────────────────────────────────────────────

    def get_balance(self):
        self._init()
        response = self.application.fetch_application_data()
        data     = response.get('UserData', {})
        return {
            'balance':  data.get('balance'),
            'username': os.getenv('AFRICASTALKING_USERNAME', 'sandbox'),
        }

    # ── SMS ───────────────────────────────────────────────────────────────────

    def send_sms(self, phone: str, message: str, sender_id: str = None) -> dict:
        self._init()
        kwargs = {'message': message, 'recipients': [phone]}
        if sender_id:
            kwargs['senderId'] = sender_id
        response   = self.sms.send(**kwargs)
        recipients = response.get('SMSMessageData', {}).get('Recipients', [{}])
        recipient  = recipients[0] if recipients else {}
        return {
            'message_id': recipient.get('messageId'),
            'status':     recipient.get('status'),
            'cost':       recipient.get('cost'),
        }


at_service = AfricasTalkingService()
