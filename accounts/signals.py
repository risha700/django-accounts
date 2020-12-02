import uuid
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from .models import Profile
User = get_user_model()


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


post_save.connect(create_user_profile, sender=User,  weak=False, dispatch_uid=str(uuid.uuid4().hex))