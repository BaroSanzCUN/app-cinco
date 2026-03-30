from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.authentication.services.authentication_service import AuthenticationService
from apps.authentication.serializers import SessionResponseSerializer
from apps.security.permissions.api_permissions import IsUserOnly


class SessionView(APIView):
    """
    Endpoint para validar sesión actual del usuario autenticado.
    """
    permission_classes = [IsUserOnly]

    @extend_schema(
        summary="Validar sesión actual",
        description=(
            "Retorna los datos del usuario autenticado según el access token "
            "en cookie httpOnly."
        ),
        responses={
            200: SessionResponseSerializer,
            401: {"detail": "No autenticado o token inválido"},
        },
    )
    def get(self, request):
        return Response(
            {
                "authenticated": True,
                "user": AuthenticationService.serialize_user(request.user),
            }
        )
