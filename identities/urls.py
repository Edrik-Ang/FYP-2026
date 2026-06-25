## urls.py file for identities app. 
## handles the routing of urls to the correct views
from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("profile/<str:username>/", views.profile_view, name="profile"),
]