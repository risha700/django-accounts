from django.contrib.auth import get_user_model
User = get_user_model()


class EmailAuthBackend(object):
    """
    Authenticate using e-mail address.
    """
    def authenticate(self, requset, username=None, password=None):
        try:
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
            return None
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class PhoneAuthBackend(object):
    """
    Authenticate using phone number
    """

    def authenticate(self, requset, username=None, password=None):
        # if username.isdigit():
        try:
            user = User.objects.get(phone=username)
            if user.check_password(password):
                return user
            return None
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class UsernameAuthBackend(object):
    """
    Overriding UserBackend
    it doesn't work on before email activation
    """

    def authenticate(self, requset, username=None, password=None):
        # if username.isdigit():
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                return user
            return None
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None