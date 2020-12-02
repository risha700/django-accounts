from django.urls import path, include, re_path, reverse_lazy
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name="register"),
    path('login/', views.LoginView.as_view(), name='login'),
    path('password_reset/',
         auth_views.PasswordResetView.as_view(
             email_template_name='post_office/accounts/password_reset_email.html',
             html_email_template_name='post_office/accounts/password_reset_email.html',
             success_url=reverse_lazy('auth:password_reset_done')
         ), name='password_reset'),

    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),

    re_path(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,35})/$',
            auth_views.PasswordResetConfirmView.as_view(
                success_url=reverse_lazy('auth:password_reset_complete')
            ), name='password_reset_done'),

    path('password_change/',
         auth_views.PasswordChangeView.as_view(
            success_url=reverse_lazy('auth:password_change_done')
         ), name='password_change'),

    path('', include('django.contrib.auth.urls')),

    path('edit/', views.ProfileEditView.as_view(), name='edit'),
    path('profile/', views.profile, name="profile"),
    path('profile/new_device/', views.alert_user, name="new_device"),
    re_path(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,35})/$',
            views.activate, name='activate'),

    path('request/activation/<int:pk>/', views.request_verification_email, name='verification_request'),
    path('phone/verify/', views.verify_phone, name='verify_phone'),
    path('phone/activate/', views.activate_phone, name='activate_phone'),
    re_path(r'^users/(?P<username>[-\w]+)/$', views.user_detail, name='user_detail'),

]

