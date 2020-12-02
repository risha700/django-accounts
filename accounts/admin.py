from django.contrib.humanize.templatetags.humanize import naturaltime
from .models import User, Profile, Device, Activity
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext, gettext_lazy as _
from django.contrib import admin
from django.contrib.admin.models import LogEntry, DELETION
from django.utils.html import escape
from django.urls import reverse
from django.utils.safestring import mark_safe


class ProfileAdmin(admin.TabularInline):
    model = Profile
    readonly_fields = ('temp_token',)


class DeviceAdmin(admin.ModelAdmin, admin.RelatedFieldListFilter):
    model = Device
    list_display = ('user', 'ip', 'machine', 'location', 'operating_system')
    list_filter = ('user', 'machine', 'location',)


admin.site.register(Device, DeviceAdmin)


class DeviceInlineAdmin(admin.TabularInline):
    model = Device
    verbose_name = 'Active Device'
    verbose_name_plural = 'Active Devices'
    extra = 0


class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'email_verified', 'phone', 'phone_verified',
                    'is_staff', 'is_superuser', 'is_active', 'last_login_location', 'last_login_at']
    actions = ['suspend_account', 'activate_account']
    inlines = (ProfileAdmin, DeviceInlineAdmin)
    list_select_related = ['profile']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        # (_('Permissions'), {
        #     'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        # }),
    )
    list_filter = ('is_active', 'profile__email_verified')

    def phone_verified(self, obj):
        return obj.profile.phone_verified

    phone_verified.boolean = True

    def email_verified(self, obj):
        return obj.profile.email_verified

    email_verified.boolean = True

    @staticmethod
    def last_login_location(obj):
        return obj.device_set.latest('created').location

    @staticmethod
    def last_login_at(obj):
        login_time = obj.last_login
        return naturaltime(login_time)

    def suspend_account(self, request, queryset):
        queryset.update(is_active=False)

    suspend_account.short_description = "Suspend user account"

    def activate_account(self, request, queryset):
        queryset.update(is_active=True)

    activate_account.short_description = "Activate user account"



admin.site.register(User, CustomUserAdmin)


class ActivityAdmin(admin.ModelAdmin):
    model = Activity
    list_display = ('user', 'verb', 'target', 'created')
    list_filter = ('created',)
    search_fields = ('verb',)


admin.site.register(Activity, ActivityAdmin)


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    date_hierarchy = 'action_time'

    list_filter = [
        'user',
        'content_type',
        'action_flag'
    ]

    search_fields = [
        'object_repr',
        'change_message'
    ]

    list_display = [
        'action_time',
        'user',
        'content_type',
        'object_link',
        'action_flag',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def object_link(self, obj):
        if obj.action_flag == DELETION:
            link = escape(obj.object_repr)
        else:
            ct = obj.content_type
            link = '<a href="%s">%s</a>' % (
                reverse('admin:%s_%s_change' % (ct.app_label, ct.model), args=[obj.object_id]),
                escape(obj.object_repr),
            )
        return mark_safe(link)

    object_link.admin_order_field = "object_repr"
    object_link.short_description = "object"