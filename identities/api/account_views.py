## identities/api/account_views.py handles the API views for account management, including email change, password change, and account deletion. It uses AccountService for business logic and ensures that the user is authenticated for these actions.
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..serializers import EmailChangeSerializer, PasswordChangeSerializer, AccountDeleteSerializer
from ..services.account_service import AccountService


class EmailChangeAPIView(APIView):
    """PATCH /api/account/email/ -- change the authenticated user's email immediately.
    Requires current password. Blacklists outstanding refresh tokens on success."""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = EmailChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = AccountService.change_email(request.user, serializer.validated_data['email'])
        return Response({'email': user.email})


class PasswordChangeAPIView(APIView):
    """PATCH /api/account/password/ -- change the authenticated user's password.
    Requires current password + confirmation of the new one."""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        AccountService.change_password(request.user, serializer.validated_data['new_password'])
        return Response(status=status.HTTP_200_OK)


class AccountDeleteAPIView(APIView):
    """DELETE /api/account/ -- permanently deletes the authenticated user's account.
    Requires current password confirmation."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        serializer = AccountDeleteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        AccountService.delete_account(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)