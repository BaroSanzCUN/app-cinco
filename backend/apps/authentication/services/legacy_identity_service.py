import jwt

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone


User = get_user_model()


class LegacyIdentityService:
    """
    Valida tokens firmados por el sistema legacy e identifica al usuario real.
    """

    @staticmethod
    def exchange_legacy_token(legacy_token: str):
        payload = LegacyIdentityService._decode_token(legacy_token)
        LegacyIdentityService._validate_replay(payload)
        user = LegacyIdentityService._resolve_user(payload)
        return user, payload

    @staticmethod
    def _decode_token(legacy_token: str) -> dict:
        if not legacy_token or not legacy_token.strip():
            raise ValueError("legacy_token es requerido")

        secret = getattr(settings, "LEGACY_JWT_SHARED_SECRET", "")
        if not secret:
            raise ValueError("LEGACY_JWT_SHARED_SECRET no está configurado")

        issuer = getattr(settings, "LEGACY_JWT_ISSUER", "legacy-app")
        audience = getattr(settings, "LEGACY_JWT_AUDIENCE", "app-cinco")
        leeway = int(getattr(settings, "LEGACY_JWT_LEEWAY_SECONDS", 30))

        try:
            return jwt.decode(
                legacy_token.strip(),
                secret,
                algorithms=["HS256"],
                issuer=issuer,
                audience=audience,
                leeway=leeway,
                options={
                    "require": ["exp", "iat", "iss", "aud"],
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise ValueError("legacy_token expirado") from exc
        except jwt.InvalidTokenError as exc:
            raise ValueError("legacy_token inválido") from exc

    @staticmethod
    def _validate_replay(payload: dict) -> None:
        jti = payload.get("jti")
        exp = payload.get("exp")

        if not jti:
            raise ValueError("legacy_token sin jti")

        if not exp:
            raise ValueError("legacy_token sin exp")

        cache_key = f"legacy_exchange_jti:{jti}"
        if cache.get(cache_key):
            raise ValueError("legacy_token ya fue utilizado")

        ttl = max(int(exp) - int(timezone.now().timestamp()), 1)
        cache.set(cache_key, True, ttl)

    @staticmethod
    def _resolve_user(payload: dict):
        user_id = payload.get("user_id")
        username = payload.get("preferred_username") or payload.get("username") or payload.get("sub")
        email = payload.get("email")

        user = None

        if user_id:
            user = User.objects.filter(id=user_id, is_active=True).first()

        if user is None and username:
            user = User.objects.filter(username=username, is_active=True).first()

        if user is None and email:
            user = User.objects.filter(email=email, is_active=True).first()

        if user is None:
            raise ValueError("No fue posible identificar un usuario válido")

        return user
