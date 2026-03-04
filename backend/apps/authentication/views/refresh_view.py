# apps/authentication/views/refresh_views.py
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from drf_spectacular.utils import extend_schema
from apps.authentication.services import rotate_refresh_token, get_device_fingerprint
from apps.authentication.serializers import (
    RefreshTokenRequestSerializer,
    RefreshTokenResponseSerializer,
)

# Logger de seguridad
security_logger = logging.getLogger('security')

class RefreshTokenView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Renovar token de acceso",
        description="Genera un nuevo access token rotando el refresh token",
        request=RefreshTokenRequestSerializer,
        responses={
            200: RefreshTokenResponseSerializer,
            400: {"detail": "refresh_token is required"},
            401: {"detail": "Invalid or expired refresh token"},
        },
        auth=[],
    )
    def post(self, request):
        # Leer refresh_token desde cookies
        refresh_token = request.COOKIES.get('refresh_token')

        if not refresh_token:
            security_logger.warning(
                f"Refresh attempt without token from IP: {request.META.get('REMOTE_ADDR')}"
            )
            return Response(
                {"detail": "refresh_token cookie is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generar fingerprint del dispositivo
        fingerprint = get_device_fingerprint(request)

        try:
            tokens = rotate_refresh_token(refresh_token, fingerprint)
            security_logger.info(
                f"Token refresh successful from IP: {request.META.get('REMOTE_ADDR')}"
            )
        except ValueError as e:
            # Log detallado del error (puede ser reuso de token)
            error_msg = str(e)
            security_logger.error(
                f"Token refresh failed: {error_msg} from IP: {request.META.get('REMOTE_ADDR')}"
            )
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Crear respuesta vacía (tokens van en cookies)
        response = Response({"detail": "Tokens refreshed successfully"}, status=status.HTTP_200_OK)
        
        # Establecer nuevos tokens en cookies
        secure_cookie = getattr(settings, 'SECURE_COOKIE', not settings.DEBUG)
        
        response.set_cookie(
            key='access_token',
            value=tokens['access_token'],
            httponly=True,
            secure=secure_cookie,
            samesite='Strict',  # Máxima protección CSRF
            max_age=15 * 60  # 15 minutos
        )
        
        response.set_cookie(
            key='refresh_token',
            value=tokens['refresh_token'],
            httponly=True,
            secure=secure_cookie,
            samesite='Strict',  # Máxima protección CSRF
            max_age=7 * 24 * 60 * 60  # 7 días
        )
        
        return response
