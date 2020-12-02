
import django
from django.contrib.auth import get_user_model
from django.test import override_settings, TestCase, Client, RequestFactory
from django.urls import reverse
from accounts.forms import UserRegistrationForm, LoginForm, TokenVerificationForm, PhoneVerificationForm
from accounts.views import verify_phone, activate_phone
from accounts.verification import Verificator
from twilio.base.exceptions import TwilioRestException

from .utils import AccountsTestCase

User = get_user_model()


class TestLoginForms(AccountsTestCase):
    def setUp(self) -> None:
        self.client = Client(enforce_csrf_checks=False)
        self.rf = RequestFactory()

    def test_register_form(self):
        form = UserRegistrationForm(data={'username': 'test', 'email': 'test@email.test',
                                          'phone': '+5571981265131', 'password': 'secret',
                                          'password2': 'secret'})
        self.assertTrue(form.is_valid())

    def test_register_form_invalid(self):
        form = UserRegistrationForm(data={'username': 'test', 'email': 'test@email.test',
                                          'phone': '+5571981265131', 'password': 'secret',
                                          'password2': 'secret2'})
        self.assertFalse(form.is_valid())

    def test_login_form_raises_locked(self):
        user = self.initialize_user(is_active=False)
        form = LoginForm(data={'username': 'test_user', 'password': 'rrrr'})
        self.assertFalse(form.is_valid())
        self.assertWarnsMessage('Your account is locked out - please contact support.', form.errors.as_json())

    def test_login_form_raises_email_unverified(self):
        self.initialize_user(email_verified=False)
        form = LoginForm(data={'username': 'test_user', 'password': 'rrrr'})
        self.assertFalse(form.is_valid())
        self.assertWarnsMessage('Please verify your email', form.errors.as_json())

    def test_login_invalid(self):
        self.initialize_user()
        form = LoginForm(data={'username': 'test_user', 'password': 'rrr'})
        self.assertFalse(form.is_valid())
        self.assertWarnsMessage('Sorry, that login was invalid. Please try again.', form.errors.as_json())


class TestPhoneActivationForms(AccountsTestCase):
    def setUp(self) -> None:
        self.client = Client(enforce_csrf_checks=False)
        self.rf = RequestFactory()

    def set_up_for_phone_verification(self):
        user = self.initialize_user(phone='+5571981265131')
        self.client.force_login(user)
        request = self.rf.post(reverse('auth:verify_phone'), data={'phone': '+5571981265131'}, follow=True)
        self.process_requests(request)
        response = verify_phone(request)
        response.client = self.client
        return request, user, response

    # @override_settings(TWILIO_PHONE_NUMBER='+15005550006')
    def test_phone_verification_form_pass(self):
        request, user, response = self.set_up_for_phone_verification()
        form = PhoneVerificationForm(data=request.POST)
        self.assertTrue(form.is_valid())
        self.assertRedirects(response, reverse('auth:activate_phone'))
        user = User.objects.get(phone=form.cleaned_data['phone'])
        self.assertTrue(user.profile.temp_token != '')
        session_phone = request.session.get('user_phone')
        self.assertEquals(user.phone, session_phone)
        self.assertTrue(len(user.profile.temp_token), 4)

    def test_phone_verification_form_fails(self):
        form = PhoneVerificationForm(data={'phone': '+16469061922'})
        self.assertFalse(form.is_valid())

    def test_phone_verification_form_valid(self):
        user = self.initialize_user(phone='+5571981265131')
        self.client.force_login(user)
        user.profile.temp_token = 1234
        user.save()
        request = self.rf.post(reverse('auth:activate_phone'),
                               data={'token': 1234}, follow=True)
        self.process_requests(request)
        request.session['user_phone'] = str(user.__dict__['phone'])  # force valid
        response = activate_phone(request)
        response.client = self.client
        self.assertRedirects(response, reverse('auth:profile'))

    def test_phone_verification_form_invalid_token(self):
        user = self.initialize_user(phone='+5571981265131')
        self.client.force_login(user)
        user.profile.temp_token = 1234
        user.save()
        request = self.rf.post(reverse('auth:activate_phone'),
                               data={'token': 1111}, follow=True)
        self.process_requests(request)
        request.session['user_phone'] = str(user.__dict__['phone'])  # force valid
        response = activate_phone(request)
        response.client = self.client
        self.assertWarnsMessage('Invalid token', response.content.decode('utf-8'))

    def test_phone_verification_form_expired_token(self):
        user = self.initialize_user(phone='+5571981265131')
        self.client.force_login(user)
        user.profile.temp_token = 1234
        user.save()
        request = self.rf.post(reverse('auth:activate_phone'),
                               data={'token': 1234}, follow=True)
        self.process_requests(request)
        response = activate_phone(request)
        response.client = self.client
        self.assertWarnsMessage('Expired request', response.content.decode('utf-8'))


    def test_phone_verification_form_invalid_request(self):
        user = self.initialize_user(phone='+5571981265131')
        self.client.force_login(user)
        user.profile.temp_token = 1234
        user.save()
        request = self.rf.post(reverse('auth:activate_phone'),
                               data={'tok': 1234}, follow=True)
        self.process_requests(request)
        request.user = user
        request.session['user_phone'] = str(user.__dict__['phone'])  # force valid
        response = activate_phone(request) # first request
        self.assertWarnsMessage('Invalid request, please request another code', response.content.decode('utf-8'))

    def test_phone_verification_form_for_non_existed_user(self):
        user = self.initialize_user(phone='+18704945574')
        self.client.force_login(user)
        form = PhoneVerificationForm(data={'phone': user.phone})
        response = self.client.post(reverse('auth:verify_phone'), data={'phone': '+18704945566'}, follow=True)
        self.assertContains(response, form.errors)

    def test_phone_verification_get(self):
        user = self.initialize_user(phone='+18704945574')
        response = self.client.get(reverse('auth:verify_phone'))
        self.assertIsInstance(response.context['form'], PhoneVerificationForm)
        self.client.force_login(user)
        response = self.client.get(reverse('auth:verify_phone'))
        self.assertIsInstance(response.context['form'], PhoneVerificationForm)

    def test_verificator_raises(self):
        request = self.rf.post(reverse('auth:verify_phone'),
                               data={'phone': '+18704945574'}, follow=True)
        self.process_requests(request)
        response = verify_phone(request)
        verificator = Verificator(request)
        self.assertFalse(verificator.verify())
        self.assertFalse(verificator.fetch_user_phone_from_session())
        with self.assertRaises(TwilioRestException):
            verificator.send_verification_sms()

    @override_settings(TWILIO_PHONE_NUMBER='+1')
    def test_phone_verification_technical_error(self):
        self.force_override_settings(target_module='accounts.verification')
        self.initialize_user(phone='+18704945574')
        response = self.client.post(reverse('auth:verify_phone'), data={'phone': '+18704945574'}, follow=True)
        self.assertContains(response, 'Technical error encountered, please try again.')
