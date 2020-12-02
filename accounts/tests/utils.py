import os

from django.contrib.auth import get_user_model
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import TestCase

User = get_user_model()


class AccountsTestCase(TestCase):
    @staticmethod
    def process_requests(req):
        middleware = SessionMiddleware()
        md = MessageMiddleware()
        middleware.process_request(req)
        md.process_request(req)

    @staticmethod
    def force_override_settings(target_module):
        import django
        import importlib
        django.setup()
        importlib.reload(importlib.import_module('app.settings'))
        importlib.reload(importlib.import_module(target_module))

    def initialize_user(self, username='test_user', email='testuser@test.com',
                        password='rrrr', phone='+16469061833',
                        is_staff=False, is_superuser=False, is_active=True, email_verified=True):
        u = User.objects.get_or_create(username=username, email=email, password=password, phone=phone)[0]
        u.profile.email_verified = email_verified
        u.is_active = is_active
        u.set_password(password)
        u.save()
        return u
    
    def generate_photo_file(self, filename='test.png', location=None):
        import io
        from PIL import Image
        file = io.BytesIO()
        image = Image.new('RGBA', size=(100, 100), color=(155, 0, 0))

        if location:
            image.save(os.path.join(location, filename), 'png')
        else:
            image.save(file, 'png')
        file.name = filename
        file.seek(0)
        return file
