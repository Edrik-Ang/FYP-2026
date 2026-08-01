# identities/api/relationship_views.py
from rest_framework import generics

from ..models import Relationship
from ..serializers import RelationshipSerializer


class RelationshipListCreateView(generics.ListCreateAPIView):
    serializer_class = RelationshipSerializer

    def get_queryset(self):
        return Relationship.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class RelationshipDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RelationshipSerializer

    def get_queryset(self):
        return Relationship.objects.filter(owner=self.request.user)