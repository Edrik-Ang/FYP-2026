## Api_urls.py file is define the API endpoint for the identities app.
from django.urls import path
from .api_views import ContextDetailView, ContextListCreateView, RegisterAPIView, LoginAPIView, LogoutAPIView, IdentityListCreateView, IdentityDetailView, RelationshipListCreateView, DisclosureRuleListCreateView, DisclosureRuleDetailView, ProfileAPIView      

urlpatterns = [
    
    path('auth/register/', RegisterAPIView.as_view(), name='api-register'),
    path('auth/login/', LoginAPIView.as_view(), name='api-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('contexts/', ContextListCreateView.as_view(), name='context-list-create'),
    path('contexts/<int:pk>/', ContextDetailView.as_view(), name='context-retrieve-update-destroy'),
    path('identities/', IdentityListCreateView.as_view(), name='identity-list-create'),
    # path('identities/<int:pk>/', IdentityDetailView.as_view(), name='identity-retrieve-update-destroy'),
    # path('relationships/', RelationshipListCreateView.as_view(), name='relationship-list-create'),    
    path('disclosure-rules/', DisclosureRuleListCreateView.as_view(), name='disclosure-rule-list-create'),
    # path('disclosure-rules/<int:pk>/', DisclosureRuleDetailView.as_view(), name='disclosure-rule-retrieve-update-destroy'),
    # path('profile/<str:username>/', ProfileAPIView.as_view(), name='profile-api'),

]