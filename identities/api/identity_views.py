# identities/api/identity_views.py
from rest_framework import generics

from ..models import IdentityProfile
from ..serializers import IdentityProfileSerializer


class IdentityListCreateView(generics.ListCreateAPIView):
    serializer_class = IdentityProfileSerializer

    def get_queryset(self):
        return IdentityProfile.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class IdentityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = IdentityProfileSerializer

    def get_queryset(self):
        return IdentityProfile.objects.filter(owner=self.request.user)