
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from ..models import ConnectionRequest
from ..serializers import ConnectionOverviewSerializer, ConnectionRequestSerializer, ConnectionRequestCreateSerializer
from ..services.relationship_service import RelationshipService


class ConnectionRequestCreateAPIView(APIView):
    """POST /api/connection-requests/ -- send a connection request. body: {'recipient_username': str}"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ConnectionRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        connection_request = RelationshipService.create_request(
            request.user, serializer.validated_data['recipient_username']
        )
        return Response(ConnectionRequestSerializer(connection_request).data, status=201)


class ConnectionOverviewAPIView(generics.ListAPIView):
    """GET /api/connection-requests/overview/ -- one entry per person the authenticated user has any connection histroy with. """
    serializer_class = ConnectionOverviewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RelationshipService.get_connection_overview(self.request.user)


class ConnectionRequestAcceptAPIView(APIView):
    """POST /api/connection-requests/<pk>/accept/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        connection_request = get_object_or_404(ConnectionRequest, pk=pk, recipient=request.user)
        RelationshipService.accept_request(connection_request, request.user)
        return Response(ConnectionRequestSerializer(connection_request).data)


class ConnectionRequestDeclineAPIView(APIView):
    """POST /api/connection-requests/<pk>/decline/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        connection_request = get_object_or_404(ConnectionRequest, pk=pk, recipient=request.user)
        RelationshipService.decline_request(connection_request, request.user)
        return Response(ConnectionRequestSerializer(connection_request).data)