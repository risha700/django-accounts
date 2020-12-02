import random
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client
from django.contrib.auth import get_user_model

User = get_user_model()

key = settings.TWILIO_API_KEY
auth_token = settings.TWILIO_AUTH_TOKEN
number = settings.TWILIO_PHONE_NUMBER



class Verificator(object):
    """
    """
    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.number = number
        self.client = Client(key, auth_token)
        self.request = request
        self.token = None
        self.phone = None

    """
    Twilio send message Api
    """

    def send_verification_sms(self):
        current_site = get_current_site(self.request)
        try:
            self.client.messages.create(
                body='Please verify your {} account - your code is : {}'.format(current_site.domain, self.token),
                from_=self.number,
                to=self.phone
            )
        except TwilioRestException:
            raise

    def generate_token(self):
        self.token = random.randint(1000, 9999)

    """ 
    params: ORM user object

    """

    def process_verification_request(self, user):
        self.phone = str(user.__dict__['phone'])
        self.generate_token()
        self.send_verification_sms()
        # persist user number in sessions for 5 minutes
        self.request.session['user_phone'] = str(user.__dict__['phone'])
        self.request.session.set_expiry(300)

    def check_token(self):
        # DB call for security
        phone = self.fetch_user_phone_from_session()
        user = User.objects.get(phone=phone)
        token = user.profile.temp_token
        if user and token != '' and token == self.request.POST['token']:
            return user
        else:
            return False

    def fetch_user_phone_from_session(self):
        return self.request.session.get('user_phone', False)

    def verify(self):
        if self.fetch_user_phone_from_session():
            self.check_token()
        else:
            return False
