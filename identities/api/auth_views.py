# identities/api/auth_views.py, handles the authentication portion for API endpoints, including registration, login, and logout functionality.
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError

from ..serializers import RegisterSerializer
from ..services.auth_service import AuthService

User = get_user_model()


class RegisterAPIView(generics.CreateAPIView):
    """POST /api/auth/register/ - create a new user (+ default public context), returns an auth token."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
    
        user = AuthService.register_user(serializer) # single save -- creates the user + default context
        tokens = AuthService.issue_token(user) # separate call to actually generate tokens
        return Response({
            'username': user.username, **tokens
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    """POST /api/auth/login/ - exchanges username-password for an auth token."""
    permission_classes = [AllowAny]

    def post(self, request):
        user = AuthService.authenticate_user(
            request,
            username=request.data.get('username'),
            password=request.data.get('password')
        )
        if user is None:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        tokens = AuthService.issue_token(user)
        return Response({
            'username': user.username, **tokens
        })


class LogoutAPIView(APIView):
    """POST /api/auth/logout/ - blacklists the given refresh token."""
    permission_classes = [AllowAny]
    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            AuthService.blacklist_refresh_token(refresh_token)
        except TokenError:
            return Response({'error': 'Invalid or expired refresh token'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)