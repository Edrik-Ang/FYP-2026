
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from ..models import ConnectionRequest
from ..serializers import ConnectionRequestSerializer, ConnectionRequestCreateSerializer
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


class IncomingConnectionRequestListAPIView(generics.ListAPIView):
    """GET /api/connection-requests/incoming/ -- pending requests sent TO the authenticated user."""
    serializer_class = ConnectionRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConnectionRequest.objects.filter(
            recipient=self.request.user, status=ConnectionRequest.PENDING
        ).select_related('sender').order_by('-created_at')


class OutgoingConnectionRequestListAPIView(generics.ListAPIView):
    """GET /api/connection-requests/outgoing/ -- requests the authenticated user has sent, any status."""
    serializer_class = ConnectionRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ConnectionRequest.objects.filter(
            sender=self.request.user
        ).select_related('recipient').order_by('-created_at')


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