## urls.py file for identities app. 
## handles the routing of urls to the correct views
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile-search/", views.profile_redirect_view, name="profile_redirect"),
    path("profile/<str:username>/", views.profile_view, name="profile"),
    path("logout/", LogoutView.as_view(next_page="login"), name="logout")
]