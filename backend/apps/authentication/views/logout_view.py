# apps/authentication/views/logout_view.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from drf_spectacular.utils import extend_schema
from apps.authentication.models import RefreshToken


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
            except RefreshToken.DoesNotExist:
                pass  # Token ya no existe o es inválido

        # Crear respuesta
        response = Response(
            {"detail": "Logout successful"},
            status=status.HTTP_200_OK
        )

        # Limpiar cookies estableciendo max_age=0
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')

        return response
