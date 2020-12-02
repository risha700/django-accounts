from django.contrib.auth import authenticate
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Profile, Device
from phonenumber_field.formfields import PhoneNumberField

from .verification import Verificator

User = get_user_model()


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Repeat password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('username', 'phone', 'email')

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Passwords don\'t match.')
        return cd['password2']


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone')


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('date_of_birth', 'photo')
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': ''}),
            # 'photo':forms.ClearableFileInput(attrs={'class':''})
        }


class LoginForm(forms.Form):
    username = forms.CharField(max_length=255, required=True,
                               help_text='You can use username, email or phone number',
                               widget=forms.TextInput(
                                   attrs={'class': ''}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': ''}), required=True)

    def __init__(self, *args, **kwargs):
        self.cached_user = None
        super(LoginForm, self).__init__(*args, **kwargs)

    def clean(self, **kwargs):
        super().clean()
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        self.cached_user = user

        if not user:
            raise forms.ValidationError("Sorry, that login was invalid. Please try again.", code='invalid')

        if not user.profile.email_verified:
            raise forms.ValidationError(
                'Please verify your email - <a href="{}"> Request a verification Link here.</a> '.format(
                    reverse('auth:verification_request', kwargs={'pk': user.pk})), code='unverified')

        if not user.is_active and user.profile.email_verified:
            raise forms.ValidationError("Your account is locked out - please contact support.", code="suspended")

        return self.cleaned_data

    def login(self, request):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        return user


class PhoneVerificationForm(forms.ModelForm):
    phone = PhoneNumberField()

    class Meta:
        model = Profile
        fields = ('phone',)

    def clean_phone(self):
        cleaned_data = super().clean()
        phone = cleaned_data.get("phone")
        try:
            User.objects.get(phone=phone)
        except User.DoesNotExist as err:
            # self.add_error('phone', err)
            raise ValidationError(err)
        return phone


class TokenVerificationForm(forms.Form):
    token = forms.CharField(
        required=True,
        widget=forms.NumberInput(
            # dirty native javascript hook
            attrs={'pattern': '/^-?\d+\.?\d*$/', 'onKeyPress': 'if(this.value.length==4) return false;'}
        )
    )

    def __init__(self, request, *args, **kwargs):
        super(TokenVerificationForm, self).__init__(*args, **kwargs)
        self.request = request

    def is_valid(self):
        try:
            verificator = Verificator(self.request)
            if verificator.fetch_user_phone_from_session():
                if verificator.check_token():
                    return True
                else:
                    self._errors = {'token': ['Invalid token']}
            else:
                self._errors = {'token': [
                    mark_safe('Expired request, <a href="{}">Request a new Token</a>'.format(reverse('auth:verify_phone')))]}
        except KeyError:
            self._errors = {'token': ['Invalid request, please request another code']}

        return super(TokenVerificationForm, self).is_valid()


class TrustedDeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['trusted']
        widgets = {
            'trusted': forms.HiddenInput()
        }

