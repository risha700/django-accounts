import os
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.http import HttpRequest
from accounts.authentication import PhoneAuthBackend, UsernameAuthBackend,EmailAuthBackend
from .utils import AccountsTestCase
User = get_user_model()


class TestAuthBackends(AccountsTestCase):
    def setUp(self) -> None:
        self.client = Client(enforce_csrf_checks=False)
        self.user = self.initialize_user(is_active=False)
        self.request = RequestFactory()

    def test_username_backend(self):
        with self.settings(AUTHENTICATION_BACKENDS=['accounts.authentication.UsernameAuthBackend']):
            request = HttpRequest()
            self.assertIsNotNone(
                UsernameAuthBackend.authenticate(self, request, username='test_user', password='rrrr')
                )
            self.assertIsNone(
                UsernameAuthBackend.authenticate(self, request, username='test_use', password='rrrr')
                )
            self.assertIsNone(UsernameAuthBackend.get_user(request, None))
            self.assertIsNone(
                UsernameAuthBackend.authenticate(self, request, username='test_user', password='rrr')
                )

    def test_phone_backend(self):
        with self.settings(AUTHENTICATION_BACKENDS=['accounts.authentication.PhoneAuthBackend']):
            request = HttpRequest()
            self.assertIsNotNone(
                PhoneAuthBackend.authenticate(self, request, username='+16469061833', password='rrrr')
                )
            self.assertIsNone(
                PhoneAuthBackend.authenticate(self, request, username='+16469061834', password='rrrr')
                )
            self.assertIsNone(PhoneAuthBackend.get_user(request, None))
            self.assertIsNone(
                PhoneAuthBackend.authenticate(self, request, username='+16469061833', password='rrr')
                )

    def test_email_backend(self):
        with self.settings(AUTHENTICATION_BACKENDS=['accounts.authentication.EmailAuthBackend']):
            request = HttpRequest()
            self.assertIsNotNone(
                EmailAuthBackend.authenticate(self, request,
                                              username='testuser@test.com', password='rrrr')
                )
            self.assertIsNone(
                EmailAuthBackend.authenticate(self, request,
                                              username='testuer@test.com', password='rrrr')
                )
            self.assertIsNone(EmailAuthBackend.get_user(request, None))
            self.assertIsNone(
                EmailAuthBackend.authenticate(self, request,
                                              username='testuser@test.com', password='rrr')
                )
