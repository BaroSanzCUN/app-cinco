from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from apps.security.models import APIKey
from apps.authentication.authentication.jwt_authentication import JWTAuthentication
from django.utils import timezone
import logging

logger = logging.getLogger('security')


class APIKeyAuthentication(BaseAuthentication):
    """
    Autenticación mediante API Key para aplicaciones externas
    Header requerido: X-API-Key: cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    Header opcional para usuario delegado:
    - X-User-Token: <jwt> o Bearer <jwt>
    - Authorization: Bearer <jwt>
    """

    keyword = "X-API-Key"
    delegated_user_header = "X-User-Token"

    def authenticate(self, request):
        api_key_obj = self.authenticate_api_key(request)

        if not api_key_obj:
            # No hay API Key, otro método de autenticación lo manejará
            return None

        user = self.authenticate_delegated_user(request)
        request.api_key = api_key_obj
        request.delegated_user = user if getattr(user, "is_authenticated", False) else None

        return (user, api_key_obj)

    def authenticate_api_key(self, request):
        api_key = request.headers.get(self.keyword, "").strip()

        if not api_key:
            return None

        if not api_key.startswith("cinco_"):
            raise AuthenticationFailed("Formato de API Key inválido")

        # Buscar la API Key por su hash
        key_hash = APIKey.hash_key(api_key)
        prefix = api_key[:APIKey.get_prefix_length()]

        try:
            api_key_obj = APIKey.objects.get(
                key_hash=key_hash,
                prefix=prefix,
                is_active=True
            )
        except APIKey.DoesNotExist:
            logger.warning(f"Intento de acceso con API Key inválida: {prefix}...")
            raise AuthenticationFailed("API Key inválida")

        # Verificar expiración
        if api_key_obj.expires_at and api_key_obj.expires_at < timezone.now():
            logger.warning(f"Intento de acceso con API Key expirada: {api_key_obj.name}")
            raise AuthenticationFailed("API Key expirada")

        # Verificar IP si está configurado
        if api_key_obj.allowed_ips:
            client_ip = self.get_client_ip(request)
            allowed_ips = [ip.strip() for ip in api_key_obj.allowed_ips.split(',')]
            if client_ip not in allowed_ips:
                logger.warning(
                    f"Acceso denegado desde IP no autorizada {client_ip} "
                    f"para API Key: {api_key_obj.name}"
                )
                raise AuthenticationFailed("IP no autorizada")

        # Actualizar último uso
        api_key_obj.last_used_at = timezone.now()
        api_key_obj.save(update_fields=['last_used_at'])

        logger.info(f"Autenticación exitosa con API Key: {api_key_obj.name}")
        return api_key_obj

    def authenticate_delegated_user(self, request):
        token = self.get_delegated_user_token(request)

        if not token:
            return AnonymousUser()

        jwt_auth = JWTAuthentication()
        user, _ = jwt_auth.authenticate_credentials(token, request)
        return user

    def get_delegated_user_token(self, request):
        delegated_header = request.headers.get(self.delegated_user_header, "").strip()

        if delegated_header:
            if delegated_header.startswith(f"{JWTAuthentication.keyword} "):
                return delegated_header.replace(f"{JWTAuthentication.keyword} ", "", 1).strip()
            return delegated_header

        jwt_auth = JWTAuthentication()
        return jwt_auth.extract_authorization_token(request)

    def get_client_ip(self, request):
        """Obtiene la IP del cliente considerando proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def authenticate_header(self, request):
        """
        Retorna el string a usar en el header WWW-Authenticate
        cuando la autenticación falla
        """
        return self.keyword
