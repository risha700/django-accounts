from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django.views.generic.base import View
from twilio.base.exceptions import TwilioRestException

from .decorators import auth_guest
from .forms import UserEditForm, ProfileEditForm, LoginForm, UserRegistrationForm, TrustedDeviceForm, \
    TokenVerificationForm, PhoneVerificationForm
from .models import Device
from .tokens import account_activation_token
from .utils import send_verification_email, create_action
from .verification import Verificator

User = get_user_model()


class RegisterView(View):
    form = UserRegistrationForm
    template_name = 'accounts/register.html'

    @method_decorator(auth_guest)
    def get(self, request, *args, **kwargs):
        user_form = self.form()
        return render(request, self.template_name, {'user_form': user_form})

    def post(self, request, *args, **kwargs):
        user_form = self.form(request.POST)
        if user_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.is_active = False
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()
            send_verification_email(request, new_user)
            messages.info(request, 'You have registered successfully, please check your email for activation link',
                          extra_tags='info still')
            create_action(new_user, 'created account')
            return render(request, self.template_name, {'new_user': new_user}, status=201)

        return render(request, self.template_name, {'user_form': user_form})


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.profile.email_verified = True
        user.save()
        login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])
        messages.success(request, 'Thanks! %s Your account is active.' % user.username,
                         extra_tags='success still')
        create_action(user, 'Activated phone')
        return redirect('auth:profile')
    else:
        return render(request, 'accounts/user/activation/invalid.html')


class LoginView(View):
    form = LoginForm
    template_name = 'registration/login.html'

    @method_decorator(auth_guest)
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'form': self.form})

    def post(self, request, *args, **kwargs):
        form = self.form(request.POST)
        if form.is_valid():
            user = form.login(request)
            if user:
                login(request, user)
                """
                catch device request and manipulate it
                """
                new_device = Device().check_device_signature(request, user)
                if new_device:
                    request.session['new_device_id'] = new_device.id
                    request.session.set_expiry(300)
                    # fire an email
                    new_device.notify_user(request, new_device)
                    return redirect('auth:new_device')

                messages.success(request, 'Welcome back {}'.format(user.username))
                create_action(user, 'logged in', user)

            return redirect(request.POST.get('next') or 'auth:profile')
        else:
            return render(request, self.template_name, {'form': form})


class ProfileEditView(LoginRequiredMixin, View):
    user_form = UserEditForm
    profile_form = ProfileEditForm
    template_name = 'accounts/edit.html'

    def get(self, request, *args, **kwargs):
        user_form = self.user_form(instance=request.user)
        profile_form = self.profile_form(instance=request.user.profile)
        return render(request, self.template_name, {'user_form': user_form, 'profile_form': profile_form})

    def post(self, request, *args, **kwargs):
        user_form = self.user_form(instance=request.user, data=request.POST)
        profile_form = self.profile_form(instance=request.user.profile, data=request.POST, files=request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            if user_form.has_changed() or profile_form.has_changed():
                user_form.save()
                profile_form.save()
                messages.success(request, 'Profile updated successfully')
                changed_fields = user_form.changed_data + profile_form.changed_data
                create_action(request.user, 'Updated %s' % changed_fields)
                return HttpResponseRedirect(reverse('auth:profile'))
        else:
            messages.warning(request, 'Error updating your profile')

        return render(request, self.template_name,
                      {'user_form': user_form, 'profile_form': profile_form})


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


def request_verification_email(request, **kwargs):
    user = User.objects.get(pk=kwargs.get('pk'))
    send_verification_email(request, user)
    messages.success(request, "Verification email has been sent to %s, please click the activation link." % user.email,
                     extra_tags='info still informative')
    # create_action(user, 'Requested a verification email')
    return redirect(reverse('auth:login'))


def alert_user(request):
    device_id = request.session.get('new_device_id', False)
    if not device_id:
        return redirect(request.POST.get('next') or 'auth:profile')

    device = Device.objects.get(id=device_id)

    device_changed_form = TrustedDeviceForm(device.__dict__)
    if request.method == 'POST':
        if device_changed_form.is_valid():
            device.trusted = True
            device.save()
            del request.session['new_device_id']
            messages.success(request, '{} has been added to your safe list'.format(
                device.machine_name if not 'Unknown-device' else 'Device'))
            return redirect(request.POST.get('next') or 'auth:profile')

    return render(request, 'accounts/user/device_changed.html', {'form': device_changed_form, 'device': device})


def activate_phone(request):
    if request.method == 'POST':
        token_form = TokenVerificationForm(request, request.POST)
        if token_form.is_valid():
            verificator = Verificator(request)
            verificator.verify()
            user = verificator.check_token()

            user.profile.phone_verified = True

            user.profile.temp_token = ''

            user.profile.save()

            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            messages.success(request, 'Thanks! %s Your phone is verified.' % user.username,
                             extra_tags='success still')

            create_action(user, 'Activated phone')
            del request.session['user_phone']
            return redirect(request.POST.get('next') or 'auth:profile')

    else:
        token_form = TokenVerificationForm(request)

    return render(request, 'accounts/user/activation/activate_phone.html', {'form': token_form})


@login_required
def user_detail(request, username):
    user = get_object_or_404(User, username=username, is_active=True)
    return render(request, 'accounts/user/detail.html', {'user': user})


def verify_phone(request):
    if request.method == 'POST':
        verification_form = PhoneVerificationForm(request.POST)
        if verification_form.is_valid():
            user_phone = verification_form.cleaned_data['phone']
            try:
                user = User.objects.get(phone=user_phone)
                verificator = Verificator(request)
                try:
                    verificator.process_verification_request(user)
                except (Exception, TwilioRestException):
                    messages.warning(request, 'Technical error encountered, please try again.')
                    return redirect('auth:verify_phone')

                user.profile.temp_token = verificator.token
                user.profile.save()

                messages.success(request, 'Verification code sent.')
                create_action(user, 'Requested phone verification')

                return redirect(request.POST.get('next') or 'auth:activate_phone')

            except User.DoesNotExist:
                user = None
    else:
        if request.user.is_authenticated:
            verification_form = PhoneVerificationForm(instance=request.user)
        else:
            verification_form = PhoneVerificationForm()

    return render(request, 'accounts/user/activation/verify_phone.html', {'form': verification_form})
