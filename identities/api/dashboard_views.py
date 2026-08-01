from identities.serializers import DashboardSerializer
from identities.services.dashboard_service import DashboardService
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class DashBoardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        dashboard = DashboardService.get_dashboard(request.user)
        serializer = DashboardSerializer(dashboard)
        return Response(serializer.data)
        