import datetime

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import Activity


class RecordsActivityMixin:
    """
    target_model: must be an instance of a model with _meta attribute you can pass it as kwargs
    """
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if request.method == 'POST':
            if response.status_code == 302:
                self.create_action(request.user,
                                   self.__class__.__name__,
                                   kwargs.get('target_model_instance', None))
        return response

    @staticmethod
    def create_action(user, verb, target=None):
        now = timezone.now()
        last_minute = now - datetime.timedelta(seconds=60)
        similar_actions = Activity.objects.filter(user_id=user.id,
                                                  verb=verb,
                                                  created__gte=last_minute)
        if target:
            target_ct = ContentType.objects.get_for_model(target)
            similar_actions = similar_actions.filter(target_ct=target_ct,
                                                     target_id=target.id)

        if not similar_actions:
            # no existing actions found
            activity = Activity(user=user, verb=verb, target=target)
            activity.save()
            return True
        return False
