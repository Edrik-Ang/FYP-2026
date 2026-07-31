## urls.py file for identities app. 
## handles the template routing of urls for the to the correct views
from django.contrib.auth import views as django_auth_views 
from django.urls import path
from .views.auth_views import WebLoginView, WebLogoutView, register_view 
from .views import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("login/", WebLoginView.as_view(), name="login"),
    path("register/", register_view, name="register"),
    path("logout/", WebLogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile-search/", views.profile_redirect_view, name="profile_redirect"),
    path("profile/<str:username>/", views.profile_view, name="profile"),

    # Web-facing password reset )
    path('password-reset/', django_auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', django_auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', django_auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', django_auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]