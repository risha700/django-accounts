import os
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from accounts.forms import UserEditForm, ProfileEditForm, PhoneVerificationForm, TrustedDeviceForm
from accounts.views import verify_phone
from accounts.views import RegisterView, ProfileEditView, LoginView
from accounts.tokens import account_activation_token
from .utils import AccountsTestCase

User = get_user_model()


class UserTest(AccountsTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.rf = RequestFactory()
        self.user = self.initialize_user()

    def tearDown(self):
        try:
            shutil.rmtree((os.path.join(settings.MEDIA_ROOT, 'test')))
        except FileNotFoundError:
            pass

    def test_login_view(self):
        response = self.client.post(reverse('auth:login'),
                                    data={'username': 'test_user', 'password': 'rrrr'}, follow=True)
        self.assertEquals(response.context['user'].username, 'test_user')
        self.assertRedirects(response, reverse('auth:new_device'))
        self.client.logout()
        response = self.client.post(reverse('auth:login'),
                                    data={'username': 'test_user', 'password': 'rrrr'}, follow=True)
        self.assertRedirects(response, reverse('auth:profile'))
        self.assertTemplateUsed('accounts/profile.html')

    def test_login_invalid(self):
        response = self.client.post(reverse('auth:login'),
                                    data={'username': 'test_user', 'password': 'rrr'}, follow=True)
        self.assertTrue(response.context['user'].is_anonymous)

    def test_request_email_verification(self):
        response = self.client.get(reverse('auth:verification_request', args=[self.user.id]), follow=True)
        self.assertRedirects(response, reverse('auth:login'))

    def test_user_list_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('auth:user_detail', args=[self.user.username]))
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/user/detail.html')

    def test_validation_update_on_change_verified_attribute(self):
        user = self.user
        self.client.force_login(user)
        self.assertTrue(user.profile.email_verified)
        user.email = 'new@test.com'
        user.phone = '+18709932214'
        user.save()
        self.assertFalse(user.profile.email_verified)
        self.assertFalse(user.profile.phone_verified)

    def test_avatar_uploads(self):

        u = User.objects.get(username='test_user')
        avatar = self.generate_photo_file()
        self.client.force_login(u)
        user_form = UserEditForm(instance=u, data=u.__dict__)
        profile_form = ProfileEditForm({'photo': avatar})
        profile_form.instance = u.profile
        res = self.client.post(reverse('auth:edit'), data={**profile_form.data, **user_form.data},
                               format='multipart', follow=True)
        u.refresh_from_db()
        upload_url = os.path.join(os.path.join(os.path.abspath(settings.MEDIA_ROOT),
                                               u.profile.photo.field.upload_to)) + 'test.png'
        self.assertEquals(res.status_code, 200)
        self.assertEquals(u.profile.photo.path, upload_url)
        u.profile.photo.delete()

    def test_cache_setup(self):
        from django.core.cache import cache
        cache.set('key', 'test_val')
        val = cache.get('key')
        self.assertEquals(val, 'test_val')


class RegistrationTest(AccountsTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.rf = RequestFactory()

    def test_register_post_valid(self):
        request = self.rf.post(reverse('auth:register'),
                                   data={'username': 'test', 'email': 'test@email.test',
                                         'phone': '+5571981265131', 'password': 'secret',
                                         'password2': 'secret'})
        self.process_requests(request)
        response = RegisterView.as_view()(request)
        self.assertEquals(response.status_code, 201)

    def test_register_post_invalid(self):
        request = self.rf.post(reverse('auth:register'),
                                   data={'username': 'test', 'email': 'test@email.test',
                                         'phone': '+5571981265131', 'password': 'secret',
                                         'password2': 'secretttt'})
        self.process_requests(request)
        response = RegisterView.as_view()(request)
        self.assertEquals(response.status_code, 200)

    def test_reset_password_process(self):
        from django.core import mail
        import re
        user = self.initialize_user()
        response = self.client.post(reverse('auth:password_reset'), data={'email': user.email}, follow=True)
        self.assertContains(response, 'We\'ve emailed you instructions for setting your password')
        self.assertRedirects(response, reverse('auth:password_reset_done'))
        url = re.findall('https?://[/-/_A-Za-z0-9/{4}].+', mail.outbox[0].body)
        reset_response = self.client.get(url[1][:-2], follow=True)
        self.assertContains(reset_response, 'New password')
        reset_done_response = self.client.post(reset_response.context['request'].path,
                                               data={'new_password1': 'secret_123444',
                                                     'new_password2': 'secret_123444'}, follow=True)
        self.assertContains(reset_done_response, 'password has been set')
        self.assertRedirects(response, reverse('auth:password_reset_done'))


class UserActivationTest(AccountsTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.rf = RequestFactory()

    def test_activate_user_email_valid(self):
        user = self.initialize_user(is_active=False, email_verified=False)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = account_activation_token.make_token(user)
        self.client.get(reverse('auth:activate', args=[uid, token]))
        user.refresh_from_db()
        self.assertTrue(user.profile.email_verified)
        self.assertTrue(user.is_active)

    def test_activate_user_email_invalid(self):
        user = self.initialize_user(is_active=False, email_verified=False)
        uid = urlsafe_base64_encode(force_bytes('grabage'))
        token = account_activation_token.make_token(user)
        self.client.get(reverse('auth:activate', args=[uid, token]))
        user.refresh_from_db()
        self.assertFalse(user.profile.email_verified)
        self.assertFalse(user.is_active)


class ProfileTest(AccountsTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.rf = RequestFactory()

    # @override_settings(ROOT_URLCONF='core.public_urls')
    def test_profile_get_superuser(self):
        user = self.initialize_user(is_superuser=True)
        self.client.force_login(user)
        response = self.client.get(reverse('auth:profile'))
        self.assertEquals(response.status_code, 200)

    def test_profile_view(self):
        user = self.initialize_user()
        self.client.force_login(user)
        self.response = self.client.get(reverse('auth:profile'))
        self.assertTemplateUsed('accounts/profile.html')
        self.assertEqual(self.response.status_code, 200)
        self.assertContains(self.response, '<strong> Welcome</strong>, {}'.format(user.username),
                            html=True, status_code=200)
        self.client.logout()
        self.response = self.client.get(reverse('auth:profile'))
        self.assertContains(self.response, '', html=False, status_code=302)
        self.assertTemplateUsed('accounts/login.html')

    def test_profile_edit_get(self):
        user = self.initialize_user()
        self.client.force_login(user)
        response = self.client.get(reverse('auth:edit'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed('accounts/edit.html')
        self.assertIsInstance(response.context['user_form'], UserEditForm)
        self.assertIsInstance(response.context['profile_form'], ProfileEditForm)

    def test_profile_edit_post_invalid(self):
        user = self.initialize_user()
        self.client.force_login(user)
        user_form = UserEditForm(instance=user, data={})
        profile_form = ProfileEditForm()
        profile_form.instance = user.profile
        response = self.client.post(reverse('auth:edit'), data={**profile_form.data, **user_form.data})
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'Error updating your profile')


class DeviceTest(AccountsTestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.rf = RequestFactory()

    def test_alert_user_device_changed(self):
        self.initialize_user()
        res = self.client.post(reverse('auth:login'),
                                    data={'username': 'test_user', 'password': 'rrrr'}, follow=True)
        device_form = res.context['form']
        self.assertTrue(device_form.is_valid())
        response = self.client.post(reverse('auth:new_device'), data=device_form.data, follow=True)
        self.assertContains(response, 'Device has been added to your safe list')

    def test_alert_user_device_changed_invalid(self):
        user = self.initialize_user()
        self.client.force_login(user)
        device_form = TrustedDeviceForm()
        response = self.client.post(reverse('auth:new_device'),
                                    device_form.data, follow=True)
        self.assertRedirects(response, reverse('auth:profile'))
