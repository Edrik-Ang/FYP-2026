# identities/api/search_views.py
from rest_framework import generics
from django.contrib.auth import get_user_model

from ..serializers import UserSearchSerializer

User = get_user_model()


class UserSearchAPIView(generics.ListAPIView):
    """GET /api/users/?search=<query> - lists other users by username."""
    serializer_class = UserSearchSerializer

    def get_queryset(self):
        queryset = User.objects.exclude(id=self.request.user.id)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(username__icontains=search)
        return queryset.order_by('username')