from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.authentication.serializers import (
    LegacyExchangeRequestSerializer,
    LoginRequestSerializer,
    LegacyLoginResponseSerializer,
    RefreshTokenRequestSerializer,
    LegacyRefreshTokenResponseSerializer,
)
from apps.authentication.services.authentication_service import AuthenticationService
from apps.authentication.services.legacy_identity_service import LegacyIdentityService
from apps.security.authentication.api_key_authentication import APIKeyAuthentication
from apps.security.permissions.api_permissions import IsAPIKeyOnly


class LegacyLoginView(APIView):
    """
    Login JSON para integraciones server-to-server.
    Requiere API Key válida y retorna tokens en el body.
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyOnly]

    @extend_schema(
        summary="Login legacy con API Key",
        description=(
            "Autentica un usuario real para una integración legacy. "
            "Requiere `X-API-Key` y retorna `access_token` y `refresh_token` en JSON."
        ),
        request=LoginRequestSerializer,
        responses={
            200: LegacyLoginResponseSerializer,
            401: {"detail": "Credenciales inválidas o API Key inválida"},
        },
    )
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        try:
            result = AuthenticationService.login(username, password, request)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "user": result["user"],
                "api_client": {
                    "id": request.auth.id,
                    "name": request.auth.name,
                    "prefix": request.auth.prefix,
                },
            },
            status=status.HTTP_200_OK,
        )


class LegacyTokenExchangeView(APIView):
    """
    Intercambio de identidad legacy sin contraseña.
    Requiere API Key válida y un token firmado por el sistema legacy.
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyOnly]

    @extend_schema(
        summary="Intercambio legacy sin contraseña",
        description=(
            "Valida un `legacy_token` firmado por el sistema externo y emite "
            "`access_token` y `refresh_token` del backend."
        ),
        request=LegacyExchangeRequestSerializer,
        responses={
            200: LegacyLoginResponseSerializer,
            401: {"detail": "legacy_token inválido o API Key inválida"},
        },
    )
    def post(self, request):
        legacy_token = request.data.get("legacy_token")

        try:
            user, _payload = LegacyIdentityService.exchange_legacy_token(legacy_token)
            result = AuthenticationService.issue_tokens_for_user(user, request)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "user": result["user"],
                "api_client": {
                    "id": request.auth.id,
                    "name": request.auth.name,
                    "prefix": request.auth.prefix,
                },
            },
            status=status.HTTP_200_OK,
        )


class LegacyRefreshTokenView(APIView):
    """
    Refresh JSON para integraciones server-to-server.
    Requiere API Key válida y refresh token en el body.
    """
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAPIKeyOnly]

    @extend_schema(
        summary="Refresh legacy con API Key",
        description=(
            "Renueva tokens para una integración legacy. "
            "Requiere `X-API-Key` y `refresh_token` en el body."
        ),
        request=RefreshTokenRequestSerializer,
        responses={
            200: LegacyRefreshTokenResponseSerializer,
            401: {"detail": "Refresh token inválido o API Key inválida"},
        },
    )
    def post(self, request):
        refresh_token = request.data.get("refresh_token")

        try:
            tokens = AuthenticationService.refresh_tokens(refresh_token, request)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(
            {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
            },
            status=status.HTTP_200_OK,
        )
