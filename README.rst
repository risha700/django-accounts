========
Accounts
========

Accounts is a Django app handles essential user security

- Email verification upon register
- Phone is enforced and mandatory "handled by Twilio sms service"
- Device access location "handled by geoip2 and maxmind db"
- Activity stream for user access

Indeed it is opinionated user app as follows:

* User class is AbstractUser has a Profile foreign key
* Profile with has fields like photo and date_of_birth

Check the docs for deep details.

Quick start
-----------

1. Add "accounts" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'accounts',
    ]

    TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['accounts/templates'],
        ...
    }]
2. Include the accounts URLconf in your project urls.py like this::

        path('accounts/',
        include(('accounts.urls', 'accounts'), namespace='auth'))


* Note: mind the namespace as it is used in templates and testing.

3. Set mandatory settings::

    # refers to the user model
    AUTH_USER_MODEL = 'accounts.User'
    MEDIA_ROOT = os.path.join(BASE_DIR, "media")
    MEDIA_URL = '/media/'
    # this is on-demand auth backends
    AUTHENTICATION_BACKENDS = [
        'accounts.authentication.EmailAuthBackend',
        'accounts.authentication.PhoneAuthBackend',
        'accounts.authentication.UsernameAuthBackend',
    ]
    # your favorite email backend
    # just for testing it is set to console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

    # maxmind db required
    # follow https://docs.djangoproject.com/en/3.1/ref/contrib/gis/geoip2/
    GEOIP_PATH = os.path.join(BASE_DIR, 'path/to/maxmind/db')

    # Twilio required sms validation
    # get keys from https://www.twilio.com/
    TWILIO_API_KEY = ""
    TWILIO_AUTH_TOKEN = ""
    TWILIO_PHONE_NUMBER = ""


4. Run ``python manage.py migrate`` to create the accounts models.

5. Start the development server and visit http://127.0.0.1:8000/accounts/login/
