## api/integration_views.py -- handles the Steam integration API endpoints, using SteamService for business logic.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework import status

from ..models import LinkedAccount, IdentityProfile
from ..serializers import LinkedAccountSerializer
from ..services.steam_service import SteamService
from ..services.identity_service import IdentityService

STEAM_MATERIALIZE_FIELDS = ['summary', 'badges', 'owned_games', 'recent_games', 'wishlist']


class SteamAuthURLAPIView(APIView):
    """
    GET /api/integrations/steam/auth-url/ -- returns the URL to redirect the user to for Steam OpenID authentication.
    But actual login still needs opening this url in a real, browser session."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'auth_url': SteamService.build_auth_url(request)})


class SteamLinkedAccountAPIView(APIView):
    """
    GET    /api/integrations/steam/  -- current linked account + cached raw_data
    DELETE /api/integrations/steam/  -- unlink
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        account = LinkedAccount.objects.filter(user=request.user, provider='steam').first()
        if not account:
            return Response({'detail': 'No linked Steam account.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(LinkedAccountSerializer(account).data)

    def delete(self, request):
        SteamService.unlink_steam_account(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SteamRefreshAPIView(APIView):
    """POST /api/integrations/steam/refresh/ -- re-fetches and caches profile data."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            account = SteamService.refresh_player_data(request.user)
        except ValidationError as e:
            detail = e.detail[0] if isinstance(e.detail, list) else e.detail
            return Response({'detail': str(detail)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LinkedAccountSerializer(account).data)


class SteamMaterializeAPIView(APIView):
    """
    POST /api/integrations/steam/materialize/
    Body: {"identity_id": <int>, "fields": ["summary", "badges", "owned_games", "recent_games", "wishlist"]}
    Copies selected raw_data fields onto the given identity as IdentityAttribute
    rows -- the same operation the steam-profile web page performs, exposed here
    for API clients / testing.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        account = LinkedAccount.objects.filter(user=request.user, provider='steam').first()
        if not account:
            return Response({'detail': 'No linked Steam account.'}, status=status.HTTP_404_NOT_FOUND)

        identity = IdentityProfile.objects.filter(pk=request.data.get('identity_id'), owner=request.user).first()
        if not identity:
            return Response({'detail': 'Invalid identity_id.'}, status=status.HTTP_400_BAD_REQUEST)

        materialized = []
        for field in request.data.get('fields', []):
            if field in STEAM_MATERIALIZE_FIELDS:
                IdentityService.set_attribute(identity, key=field, value=account.raw_data.get(field), source='steam')
                materialized.append(field)

        return Response({'identity_id': identity.id, 'materialized_fields': materialized})