from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from apps.authentication.services.authentication_service import AuthenticationService


class HealthCheckView(APIView):
    """
    Health check endpoint para CI/CD y monitoreo.
    Delega validación de conexiones a AuthenticationService.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary="Health Check",
        description="Verifica el estado del backend y conexiones a bases de datos",
        responses={
            200: {
                "description": "Sistema saludable",
                "example": {
                    "status": "healthy",
                    "service": "app-cinco-backend",
                    "databases": {
                        "default": "connected",
                        "azul": "connected"
                    }
                }
            },
            503: {
                "description": "Sistema no disponible",
                "example": {
                    "status": "unhealthy",
                    "service": "app-cinco-backend",
                    "error": "Database connection failed"
                }
            }
        },
        auth=[]
    )
    def get(self, request):
        health_status = AuthenticationService.health_check()

        # Si el estado es unhealthy, retornar 503
        if health_status["status"] == "unhealthy":
            return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(health_status, status=status.HTTP_200_OK)
