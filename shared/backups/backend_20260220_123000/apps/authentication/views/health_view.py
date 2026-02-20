from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db import connections
from drf_spectacular.utils import extend_schema


class HealthCheckView(APIView):
    """
    Health check endpoint para CI/CD y monitoreo
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
        try:
            # Verificar conexión a base de datos default
            connections['default'].ensure_connection()
            db_default_status = "connected"
        except Exception as e:
            db_default_status = f"error: {str(e)}"

        try:
            # Verificar conexión a base de datos azul
            connections['azul'].ensure_connection()
            db_azul_status = "connected"
        except Exception as e:
            db_azul_status = f"error: {str(e)}"

        # Si alguna BD falló, retornar 503
        if "error" in db_default_status or "error" in db_azul_status:
            return Response({
                "status": "unhealthy",
                "service": "app-cinco-backend",
                "databases": {
                    "default": db_default_status,
                    "azul": db_azul_status
                }
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({
            "status": "healthy",
            "service": "app-cinco-backend",
            "databases": {
                "default": db_default_status,
                "azul": db_azul_status
            }
        }, status=status.HTTP_200_OK)
