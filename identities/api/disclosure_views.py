# identities/api/disclosure_views.py
from identities.services.disclosure_service import DisclosureService
from rest_framework import generics

from ..models import DisclosureRule
from ..serializers import DisclosureRuleSerializer


class DisclosureRuleListCreateView(generics.ListCreateAPIView):
    serializer_class = DisclosureRuleSerializer

    def get_queryset(self):
        return DisclosureService.list_rules(self.request.user)

    def perform_create(self, serializer):
        DisclosureService.create_rule(self.request.user, serializer)


class DisclosureRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DisclosureRuleSerializer

    def get_queryset(self):
        return DisclosureService.list_rules(self.request.user)