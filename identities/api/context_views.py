# identities/api/context_views.py
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from ..models import Context
from ..serializers import ContextSerializer


class ContextListCreateView(generics.ListCreateAPIView):
    serializer_class = ContextSerializer

    def get_queryset(self):
        return Context.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ContextDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ContextSerializer

    def get_queryset(self):
        return Context.objects.filter(owner=self.request.user)

    def perform_destroy(self, instance):
        if instance.is_public_default:
            raise ValidationError("Cannot delete the default public context.")
        instance.delete()