## Api_urls.py file is define the API endpoint for the identities app.
from django.urls import path
from . import api_views

urlpatterns = [
    
    path('auth/register/', api_views.RegisterAPIView.as_view()),
    path('auth/login/', api_views.LoginAPIView.as_view()),
    path('auth/logout/', api_views.LogoutAPIView.as_view()),
    path('identities/', api_views.IdentityListCreateView.as_view(), name='identity-list-create'),
    path('identities/<int:pk>/', api_views.IdentityDetailView.as_view(), name='identity-retrieve-update-destroy'),
    path('relationships/', api_views.RelationshipListCreateView.as_view(), name='relationship-list-create'),    
    path('disclosure-rules/', api_views.DisclosureRuleListCreateView.as_view(), name='disclosure-rule-list-create'),
    path('disclosure-rules/<int:pk>/', api_views.DisclosureRuleDetailView.as_view(), name='disclosure-rule-retrieve-update-destroy'),
    path('profile/<str:username>/', api_views.ProfileAPIView.as_view(), name='profile-api'),

]