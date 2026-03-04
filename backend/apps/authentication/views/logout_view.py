# apps/authentication/views/logout_view.py
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from drf_spectacular.utils import extend_schema
from apps.authentication.models import RefreshToken

# Logger de seguridad
security_logger = logging.getLogger('security')


class LogoutView(APIView):
    """
    Endpoint para cerrar sesión del usuario.
    Revoca el refresh token y limpia las cookies.
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Cerrar sesión",
        description="Revoca el refresh token y limpia las cookies de autenticación",
        responses={
            200: {"detail": "Logout successful"},
            400: {"detail": "No refresh token found"},
        },
        auth=[],
    )
    def post(self, request):
        # Obtener refresh_token desde cookies
        refresh_token = request.COOKIES.get('refresh_token')

        # Si existe el token, revocarlo en la base de datos
        if refresh_token:
            try:
                token_obj = RefreshToken.objects.get(token=refresh_token)
                token_obj.revoke()
                security_logger.info(
                    f"User logged out successfully (User ID: {token_obj.user.id}) from IP: {request.META.get('REMOTE_ADDR')}"
                )
            except RefreshToken.DoesNotExist:
                security_logger.warning(
                    f"Logout attempt with invalid token from IP: {request.META.get('REMOTE_ADDR')}"
                )
                pass  # Token ya no existe o es inválido
        else:
            security_logger.warning(
                f"Logout attempt without token from IP: {request.META.get('REMOTE_ADDR')}"
            )

        # Crear respuesta
        response = Response(
            {"detail": "Logout successful"},
            status=status.HTTP_200_OK
        )

        # Limpiar cookies estableciendo max_age=0
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')

        return response
