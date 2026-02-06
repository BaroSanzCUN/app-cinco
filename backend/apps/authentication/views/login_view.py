from operator import ge
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from drf_spectacular.utils import extend_schema

from apps.authentication.services import (
    generate_access_token, 
    generate_refresh_token
)
from apps.authentication.serializers import (
    LoginRequestSerializer,
    LoginResponseSerializer
)

class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Login de usuario",
        description="Autenticación de usuario y generación de tokens JWT",
        request=LoginRequestSerializer,
        responses={
            200: LoginResponseSerializer,
            400: {"detail": "Usuario y contraseña requeridos"},
            401: {"detail": "Credenciales inválidas"},
        },
        auth=[],
    )
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "Usuario y contraseña requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {"detail": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        access = generate_access_token(user)
        refresh = generate_refresh_token(user)

        return Response({
            "access": access,
            "refresh": refresh.token,
            "user": {
                "id": user.id,
                "username": user.username,
                "is_superuser": user.is_superuser
            }
        })
