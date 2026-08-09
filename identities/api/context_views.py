# identities/api/context_views.py handles the API views for context management, using the ContextService for business logic.
## Main driver for context management and context html page.
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from ..models import Context
from ..serializers import ContextSerializer
from identities.services.context_service import ContextService


class ContextListCreateView(generics.ListCreateAPIView):

    serializer_class = ContextSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ContextService.get_contexts(self.request.user)

    
    def perform_create(self, serializer):
        ContextService.create_context(self.request.user, serializer)

class ContextDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContextSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Context.objects.filter(owner=self.request.user)

    def perform_update(self, serializer):
        ContextService.update_context(self.get_object(), serializer)

    def perform_destroy(self, instance):
        ContextService.delete_context(instance)