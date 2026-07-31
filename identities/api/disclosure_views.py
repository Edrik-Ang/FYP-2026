# identities/api/disclosure_views.py
from rest_framework import generics

from ..models import DisclosureRule
from ..serializers import DisclosureRuleSerializer


class DisclosureRuleListCreateView(generics.ListCreateAPIView):
    serializer_class = DisclosureRuleSerializer

    def get_queryset(self):
        return DisclosureRule.objects.filter(identity__owner=self.request.user)


class DisclosureRuleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DisclosureRuleSerializer

    def get_queryset(self):
        return DisclosureRule.objects.filter(identity__owner=self.request.user)