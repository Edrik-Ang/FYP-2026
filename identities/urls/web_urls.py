## urls.py file for identities app. 
## handles the template routing of urls for the to the correct views
from django.contrib.auth import views as django_auth_views 
from django.urls import path

from identities.views.context_views import context_create_view, context_delete_view, context_edit_view, context_list_view
from identities.views.identity_views import identity_create_view, identity_delete_view, identity_edit_view, identity_list_view
from identities.views.relationship_views import relationship_create_view, relationship_delete_view, relationship_delete_view, relationship_edit_view, relationship_list_view, relationship_preview_view
from ..views import (
    home_view, dashboard_view, profile_view, profile_redirect_view,
    WebLoginView, WebLogoutView, register_view,
)

urlpatterns = [
    path('', home_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('profile/', profile_redirect_view, name='profile-redirect'),
    path('profile/<str:username>/', profile_view, name='profile'),

    path('login/', WebLoginView.as_view(), name='login'),
    path('logout/', WebLogoutView.as_view(), name='logout'),
    path('register/', register_view, name='register'),

    # Web-facing password reset )
    path('password-reset/', django_auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', django_auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', django_auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', django_auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    ## contexts urls
    path('contexts/', context_list_view, name='context-list'),
    path('contexts/new/', context_create_view, name='context-create'),
    path('contexts/<int:pk>/edit/', context_edit_view, name='context-edit'),
    path('contexts/<int:pk>/delete/', context_delete_view, name='context-delete'),  

    ## identity urls
    path('identities/', identity_list_view, name='identity-list'),
    path('identities/new/', identity_create_view, name='identity-create'),
    path('identities/<int:pk>/edit/', identity_edit_view, name='identity-edit'),
    path('identities/<int:pk>/delete/', identity_delete_view, name='identity-delete'),

    path('relationships/', relationship_list_view, name='relationship-list'),
    path('relationships/new/', relationship_create_view, name='relationship-create'),
    path('relationships/<int:pk>/edit/', relationship_edit_view, name='relationship-edit'),
    path('relationships/<int:pk>/delete/', relationship_delete_view, name='relationship-delete'),
    path('relationships/<int:pk>/preview/', relationship_preview_view, name='relationship-preview'),

]