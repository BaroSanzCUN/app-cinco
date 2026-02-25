import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from apps.authentication.services import validate_device_fingerprint

User = get_user_model()

class JWTAuthentication(BaseAuthentication):

    keyword = "Bearer"

    def authenticate(self, request):
        # Prioridad: cookie > header (para soportar ambos durante transición)
        token = request.COOKIES.get('access_token')
        
        if not token:
            # Fallback a header Authorization (para endpoints que no usan cookies)
            header = request.headers.get("Authorization")
            
            if not header:
                return None  # permite endpoints públicos

            if not header.startswith(self.keyword):
                raise AuthenticationFailed("Formato de Authorization inválido")

            token = header.replace(self.keyword, "").strip()

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"]
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Token expirado")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Token inválido")

        user_id = payload.get("user_id")

        if not user_id:
            raise AuthenticationFailed("Token sin usuario")

        # Validar fingerprint si está presente en el token
        token_fingerprint = payload.get("fp")
        if token_fingerprint:
            if not validate_device_fingerprint(request, token_fingerprint):
                raise AuthenticationFailed("Token usado desde dispositivo no autorizado")

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            raise AuthenticationFailed("Usuario no válido")

        return (user, token)
