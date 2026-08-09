# identities/api/profile_views.py
from identities.services.disclosure_service import DisclosureService
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from ..serializers import VisibleIdentitySerializer

User = get_user_model()


class ProfileAPIView(APIView):
    """GET /api/profile/<username>/ - returns only what the requesting user is allowed to see."""
    def get(self, request, username):
        owner = get_object_or_404(User, username=username)
        visible_data = DisclosureService.get_visible_identities(owner, request.user)
        serializer = VisibleIdentitySerializer(visible_data, many=True)
        return Response({'owner': owner.username, 'visible_identities': serializer.data})