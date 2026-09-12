from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from ..serializers import UserProfileSerializer


class UserProfileSettingsAPIView(generics.RetrieveUpdateAPIView):
    """GET / PATCH /api/profile/settings -- the authenticated user's own account settings"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.profile