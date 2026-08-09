# identities/api/relationship_views.py handles the API views for relationship management, using RelationshipService for business logic.
from identities.services.relationship_service import RelationshipService
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from ..models import Relationship
from ..serializers import RelationshipSerializer, VisibleIdentitySerializer
from ..services.disclosure_service import DisclosureService


class RelationshipListCreateView(generics.ListCreateAPIView):
    serializer_class = RelationshipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RelationshipService.list_relationships(self.request.user)

    def perform_create(self, serializer):
        RelationshipService.create_relationship(self.request.user, serializer)

class RelationshipDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RelationshipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RelationshipService.list_relationships(self.request.user)

    def perform_update(self, serializer):
        RelationshipService.update_relationship(serializer)

    def perform_destroy(self, instance):
        RelationshipService.delete_relationship(instance)

class RelationshipPreviewAPIview(APIView):
    """GET /api/relationships/<id>/preview/ -- what this relationship's target-user would see viewing my profile right now, from the current context tags. Reuses get_visible_identities
    no new disclosure logic."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        relationship = get_object_or_404(Relationship, pk=pk, owner=request.user)
        visible_data = DisclosureService.get_visible_identities(request.user, relationship.target_user)
        serializer = VisibleIdentitySerializer(visible_data, many=True)
        return Response({'viewed_as': relationship.target_user.username, 'visible_identities': serializer.data})
    