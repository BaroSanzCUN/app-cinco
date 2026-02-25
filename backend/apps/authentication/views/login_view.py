from operator import ge
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.conf import settings
from drf_spectacular.utils import extend_schema

from apps.authentication.services import (
    generate_access_token, 
    generate_refresh_token,
    get_device_fingerprint
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

        # Generar fingerprint del dispositivo para seguridad adicional
        fingerprint = get_device_fingerprint(request)
        
        # Generar tokens con fingerprint
        access = generate_access_token(user, fingerprint)
        refresh = generate_refresh_token(user)
        
        # Get employee photo
        # employee = user.empleado
        # foto = employee.foto or employee.link_foto if employee else None
        
        # Crear respuesta solo con datos del usuario
        response = Response({
            "user": {
                "id": user.id,
                "username": user.username,
                "nombre": user.first_name,
                "apellido": user.last_name,
                "email": user.email,
                "is_superuser": user.is_superuser,
                # "foto": foto
            }
        })
        
        # Establecer tokens en cookies httpOnly (protección XSS)
        secure_cookie = getattr(settings, 'SECURE_COOKIE', not settings.DEBUG)
        
        response.set_cookie(
            key='access_token',
            value=access,
            httponly=True,  # No accesible desde JavaScript
            secure=secure_cookie,  # Solo HTTPS en producción
            samesite='Lax',  # Protección CSRF
            max_age=15 * 60  # 15 minutos
        )
        
        response.set_cookie(
            key='refresh_token',
            value=refresh.token,
            httponly=True,
            secure=secure_cookie,
            samesite='Lax',
            max_age=7 * 24 * 60 * 60  # 7 días
        )
        
        return response
