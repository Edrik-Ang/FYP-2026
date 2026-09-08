# api/api_github.py handles API views for Github integration.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from ..models import LinkedAccount, IdentityProfile
from ..services.github_service import GITHUB_MATERIALIZE_FIELDS
from ..services.identity_service import IdentityService

class GithubMaterialAPIView(APIView):
    """
    POST /api/integrations/github/materialize/
    Body: {"identity_id": <int>, "fields": ["login", "name", "avatar", "html_url", "bio"]}"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        account = LinkedAccount.objects.filter(user=request.user, provider='github').first()
        if not account:
            return Response({'detail': "No linked Github account."}, status=status.HTTP_404_NOT_FOUND)

        identity = IdentityProfile.objects.filter(pk=request.data.get('identity_id'), owner=request.user).first()
        if not identity:
            return Response({'detail': "Identity not found."}, status=status.HTTP_404_NOT_FOUND)

        for field in request.data.get('fields', []):
            if field in GITHUB_MATERIALIZE_FIELDS:
                try:
                    IdentityService.set_attribute(identity, key=field, value=account.raw_data.get(field), source='github')
                except Exception as e:
                    return Response({'detail': f"Error materializing field '{field}': {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': "Fields materialized successfully."}, status=status.HTTP_200_OK)