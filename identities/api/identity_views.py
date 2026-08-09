# identities/api/identity_views.py
from identities.services.identity_service import IdentityService
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from ..serializers import IdentityProfileSerializer


class IdentityListCreateView(generics.ListCreateAPIView):
    serializer_class = IdentityProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return IdentityService.list_identities(self.request.user)

    
    def perform_create(self, serializer):
        IdentityService.create_identity(self.request.user, serializer)


class IdentityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = IdentityProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return IdentityService.list_identities(self.request.user)

    def perform_update(self, serializer):
        IdentityService.update_identity(serializer)

    def perform_destroy(self, instance):
        IdentityService.delete_identity(instance)