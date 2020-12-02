from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import ImageField
import datetime

from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import account_activation_token

# not used
# def _set_upload_space():
#     cs = connection.tenant.schema_name
#     tn = get_tenant_model().objects.get(schema_name=cs)
#     return '{}/uploads/users/%Y/%m/%d'.format(tn.domain_url)


class CustomImageField(ImageField):
    def save_form_data(self, instance, data):
        if data is not None:
            file = getattr(instance, self.attname)
            if file != data:
                file.delete(save=False)
        super(CustomImageField, self).save_form_data(instance, data)


def send_verification_email(request, user):
    current_site = get_current_site(request)
    subject = 'Activate Your {} Account'.format(current_site)
    message = render_to_string('post_office/accounts/activation_email.html', {
        'user': user,
        'domain': current_site.domain,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    user.email_user(subject, message, html_message=message)


def create_action(user, verb, target=None):
    """
    helper function to create activity

    :param user: user object
    :param verb: string [create, change, delete, add]
    :param target: target model string defaults to None

    """
    now = timezone.now()
    last_minute = now - datetime.timedelta(seconds=60)
    from .models import Activity
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


def assign_permissions(grp_name: str = 'owner_admin', ltd_access_apps: list = [],
                        full_access_apps: list = [], restricted_models: list = []):
    """ shortcut to assign permissions

    :param grp_name: string of a group name example: 'owner_admin'.

    :param ltd_access_apps: a list of dictionary [{'app_name':['actions']}]
        or [{'app_name.model':['add','change','delete']}]

        example:[{'accounts': ['delete']},]
        Note: in case used dotted notation for the same app_name then
        you have to assign it all with app_name.model style otherwise the app_name only will take precedence.

    :param full_access_apps: list  ['app_name']  example: ['accounts', 'store']

    :param restricted_models: list of dotted notation ['app_name.model'] or even ['app_name.model.permission']
        example: ['accounts.device'] to remove any ltd_access or full_access model level permissions

    * examples:

       .. code-block:: python

            assign_permissions(ltd_access=[{'accounts':['delete']}], full_access=['store'],
            restricted_models=['accounts.activity'])

            assign_permissions(
            ltd_access=[{'accounts':['delete']}, {'clients':['delete','add','change']}],
            full_access=['store'],
            restricted_models=['accounts.activity.add','accounts.activity.delete']
            )

    """
    owner_admin = Group.objects.get_or_create(name=grp_name)[0]
    # start on clean group permissions
    owner_admin.permissions.clear()
    to_remove = set()
    to_escalate = set()
    for _app in full_access_apps:
        to_escalate.add(Permission.objects.filter(content_type__app_label=_app))

    for mod in restricted_models:
        try:
            """remove specific permission"""
            app_label, model, perm = mod.split('.')
            to_remove.add(Permission.objects.filter(content_type__app_label=app_label,
                                                    content_type__model=model, codename__icontains=perm))
        except ValueError:
            """restrict the whole model"""
            app_label, model = mod.split('.', 1)
            to_remove.add(Permission.objects.filter(content_type__app_label=app_label, content_type__model=model))

    for ltd_app_list in ltd_access_apps:
        app_label = list(ltd_app_list.keys())[0]
        app_available_perms = Permission.objects.filter(
                content_type__app_label=app_label)
        if '.' in app_label:
            app_label, model_name = list(ltd_app_list.keys())[0].split('.', 1)
            app_available_perms = Permission.objects.filter(
                content_type__app_label=app_label, content_type__model=model_name)
        for privilege in list(ltd_app_list.values())[0]:
            app_available_perms = app_available_perms.exclude(codename__icontains=privilege)

        to_escalate.add(app_available_perms)

    for perm in list(to_escalate):
        owner_admin.permissions.add(*perm)
    for perm in list(to_remove):
        owner_admin.permissions.remove(*perm)
    return owner_admin
