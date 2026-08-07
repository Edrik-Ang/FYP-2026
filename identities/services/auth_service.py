## auth_service.py -- authentication business logic, same pattern as ContextService/IndentityService/etc. 
## Splits user creation from token generation: web generation uses session-based auth, while API uses JWT. 

from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

class AuthService:
    @staticmethod
    def register_user(serializer):
        """Create user via registerSerializer.create()
        """
        return serializer.save()

    @staticmethod
    def authenticate_user(request,username, password):
        """Authenticate user via Django's built-in authenticate() function.
        Returns user object if successful, None otherwise.
        """
        return authenticate(request, username=username, password=password)

    @staticmethod
    def issue_token(user):
        """Issue new refresh and access tokens for the given user using DRF SimpleJWT."""
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

    @staticmethod
    def blacklist_refresh_token(refresh_token):
        """Raise TokenError on invalid/expired token, caller(view) left to translate into HTTP response"""
        RefreshToken(refresh_token).blacklist()