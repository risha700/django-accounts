

from functools import wraps

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
# from ratelimit.decorators import ratelimit
# from accounts.utils import rate_limit_remote_user_header_key

def auth_guest(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url=None):
    """
    Decorator for views that checks that the user is guest in, redirecting
    to the profile page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_anonymous,
        login_url='auth:profile',
        redirect_field_name=None
    )
    if function:
        return actual_decorator(function)

    return actual_decorator


# def records_activity(function):
#     @wraps(function)
#     def wrap(request, *args, **kwargs):
#         if request.method == 'POST':
#             response = function(request, *args, **kwargs)
#             if response.status_code == 302:
#                 from .utils import create_action
#                 create_action(request.user, function.__name__)
#             return response
#         return function(request, *args, **kwargs)
#     return wrap
