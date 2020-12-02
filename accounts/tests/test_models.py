from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import override_settings, Client
from django.urls import reverse
from accounts.forms import LoginForm
from accounts.models import Device
from accounts.apps import AccountsConfig
from .utils import AccountsTestCase

User = get_user_model()


class TestAccounts(AccountsTestCase):
    def setUp(self) -> None:
        self.client = Client(enforce_csrf_checks=False)

    # def test_homepage_loads(self):
    #     res = self.client.get(reverse('home'))
    #     self.assertEqual(res.status_code, 200)

    def test_login_page_loads(self):
        res = self.client.get(reverse('auth:login'))
        self.assertEqual(res.status_code, 200)

    def test_register_page_loads(self):
        res = self.client.get(reverse('auth:register'))
        self.assertEqual(res.status_code, 200)

    def test_login(self):
        self.initialize_user()
        login_form = LoginForm(data={'username': 'test_user', 'password': 'rrrr'})
        self.assertTrue(login_form.is_valid())
        login_response = self.client.post(reverse('auth:login'), data=login_form.data, format='text/html', follow=True)
        self.assertEquals(login_response.status_code, 200)
        self.assertEquals(str(login_response.context['user']), 'test_user')

    def test_user_absolute_url(self):
        user = self.initialize_user()
        self.assertEquals(user.get_absolute_url(), reverse('auth:user_detail', args=[user.username]))
        self.assertEquals(user.profile.__str__(), 'Profile for user test_user')

    def test_new_device_methods(self):
        user = self.initialize_user()
        device, _ = Device.objects.get_or_create(user=user, machine='Mac',
                                                 browser='Chrome', operating_system='OS',
                                                 ip='127.0.0.1', location='USA')
        self.assertEquals(device.get_absolute_url(), reverse('auth:new_device'))
        self.assertEquals(device.__str__(), 'Mac from 127.0.0.1 - USA')


class AccountsConfigTest(AccountsTestCase):
    def test_apps(self):
        self.assertEqual(AccountsConfig.name, 'accounts')
        self.assertEqual(apps.get_app_config('accounts').name, 'accounts')

