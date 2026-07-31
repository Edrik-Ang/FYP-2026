## Api_urls.py file is define the API endpoint URL paths for the identities app.
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView
from ..api import (
    RegisterAPIView, LoginAPIView, LogoutAPIView,
    ContextListCreateView, ContextDetailView,
    IdentityListCreateView, IdentityDetailView,
    RelationshipListCreateView, RelationshipDetailView,
    DisclosureRuleListCreateView, DisclosureRuleDetailView,
    ProfileAPIView, UserSearchAPIView,
)


urlpatterns = [

    ### APIs for authentication
    ### Authentication
    path('auth/register/', RegisterAPIView.as_view(), name='api-register'),
    path('auth/login/', LoginAPIView.as_view(), name='api-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='api-token-refresh'),

    ## API for password resets (Later do)
    path('password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset_api')),



    ## API for email verification (Later do)

    ### APIs for contexts
    ## /api/contexts/

    ### APIs for identities
    ## /api/identities/
    ## /api/identities/{id}/

    ### APIs for relationships
    ## /api/relationships/



    ### APIs for profiles
    ## GET /user/me own full profile
    ## PATCH /user/me update profile (partial update, not full replace)
    ## DELETE /user/me Delete profile
    ## PATCH /user/me/visibility Update field level privacy settings for own profile

    ### Profile for others
    ## GET /users/:id public view of someone else profile, respecting their visibility settings server-side (not client-side)
    ## GET /users/username:username -- support username lookup, currently only display all in web app. (need look into different ways for this)
    
    ### Search
    ## GET /search/users?q= ... keyword/username search, default, and always on.
    ## POST /search/users with filters for more advanced search, e.g. by relationship type, context, etc. (later do)

    ### API for STEAM (later do)
    ## GET /steam/link or POST /steam/link to link a steam account to the user profile
    ## GET /steam/callback -- Steam redirects back here, verify and store steamID.
    ## DELETE /steam/unlink -- unlink steam account from user profile
    ## GET /users/:id/steam -- public steam data for profile (games, playtime), separate from the core profile since different data source/rate limit and might fail independently of the core profile..





    ### Identity domain
    path('contexts/', ContextListCreateView.as_view(), name='context-list-create'),
    path('contexts/<int:pk>/', ContextDetailView.as_view(), name='context-retrieve-update-destroy'),
    path('identities/', IdentityListCreateView.as_view(), name='identity-list-create'),
    path('identities/<int:pk>/', IdentityDetailView.as_view(), name='identity-retrieve-update-destroy'),
    path('relationships/', RelationshipListCreateView.as_view(), name='relationship-list-create'),
    path('relationships/<int:pk>/', RelationshipDetailView.as_view(), name='relationship-retrieve-destroy'),
    path('disclosure-rules/', DisclosureRuleListCreateView.as_view(), name='disclosure-rule-list-create'),
    path('disclosure-rules/<int:pk>/', DisclosureRuleDetailView.as_view(), name='disclosure-rule-retrieve-update-destroy'),
    path('profile/<str:username>/', ProfileAPIView.as_view(), name='profile-api'),
    path('users/', UserSearchAPIView.as_view(), name='user-search-api'),

    ## Look into refactoring URL patterns, maybe look into document based API.
    ##CRUD for Each model

]
