from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.db import models

from django.template.loader import render_to_string
from django.urls import reverse

from accounts.utils import CustomImageField
from phonenumber_field.modelfields import PhoneNumberField

from .device_generator import get_user_agent, get_location, get_ip


class User(AbstractUser):
    phone = PhoneNumberField(unique=True, help_text='Mobile number')

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self._original_phone = self.phone
        self._original_email = self.email

    class Meta:
        unique_together = ['email', 'phone']

    def get_absolute_url(self):
        return reverse('auth:user_detail', args=[self.username])

    def save(self, *args, **kwargs):
        self.check_verified_fields()
        super(User, self).save(*args, **kwargs)

    def check_verified_fields(self):
        if hasattr(self, 'profile'):
            if self._original_phone is not None:
                if self.phone != self._original_phone:
                    self.profile.phone_verified = False
            if self._original_email is not None:
                if self.email != self._original_email:
                    self.profile.email_verified = False
                self.profile.save()


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_of_birth = models.DateField(blank=True, null=True)
    photo = CustomImageField(upload_to='uploads/users/avatar/', blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    temp_token = models.CharField(blank=True, default='', max_length=100)

    def __str__(self):
        return 'Profile for user {}'.format(self.user.username)


class Device(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    machine = models.CharField(max_length=255, blank=False, null=False)
    browser = models.CharField(max_length=255, blank=False, null=False)
    operating_system = models.CharField(max_length=255, blank=False, null=False)
    ip = models.GenericIPAddressField(max_length=255)
    location = models.CharField(max_length=255, blank=False, null=False)
    trusted = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return '{} from {} - {}'.format(self.machine, self.ip, self.location)

    def get_absolute_url(self):
        return reverse('auth:new_device')

    """
    :returns device object
    """
    def generate_new_signature(self, request):
        user_agent = get_user_agent(request)
        device = '{0} {1}, {2}'.format(user_agent.device.brand, user_agent.get_device(), user_agent.device.family)
        new_device = Device.objects.create(
            user=request.user,
            machine=request.META.get('REMOTE_USER', device),
            browser=user_agent.get_browser(),
            operating_system=user_agent.get_os(),
            location=get_location(request),
            ip=get_ip(request),
        )
        return new_device

    def check_device_signature(self, request, user):
        """Keep record of user's Host and machine Mac_address
        """
        list_user_trusted_devices = Device.objects.filter(user=user)
        login_ip = get_ip(request)
        if login_ip in list_user_trusted_devices.values_list('ip', flat=True):
            return False
        else:
            # TODO: security steps TFA
            logged_in_device = self.generate_new_signature(request)
            return logged_in_device

    @staticmethod
    def notify_user(request, device):
        current_site = get_current_site(request)
        subject = 'Unusual activity on your {} Account'.format(current_site)
        message = render_to_string('post_office/accounts/device_changed_email.html', {
            'user': request.user,
            'domain': current_site.domain,
            'device': device
        })
        request.user.email_user(subject, message, html_message=message)


class Activity(models.Model):
    user = models.ForeignKey(User,
                             related_name='actions',
                             db_index=True,
                             on_delete=models.CASCADE)
    verb = models.CharField(max_length=255)
    target_ct = models.ForeignKey(ContentType,
                                  blank=True,
                                  null=True,
                                  related_name='target_obj',
                                  on_delete=models.CASCADE)
    target_id = models.PositiveIntegerField(null=True,
                                            blank=True,
                                            db_index=True)
    target = GenericForeignKey('target_ct', 'target_id')
    created = models.DateTimeField(auto_now_add=True,
                                   db_index=True)

    class Meta:
        ordering = ('-created',)
        verbose_name_plural = 'activities'
