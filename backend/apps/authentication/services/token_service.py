# apps/authentication/services/refresh_service.py
from datetime import timedelta
from django.utils import timezone
from apps.authentication.models import RefreshToken
from .jwt_service import generate_access_token

def rotate_refresh_token(old_token_str, fingerprint=None):
    """
    Rota el refresh token generando uno nuevo y revocando el anterior.
    
    Args:
        old_token_str: Token de refresh actual
        fingerprint: Huella digital del dispositivo (opcional pero recomendado)
    
    Returns:
        dict: Diccionario con access_token y refresh_token nuevos
    """
    try:
        old_token = RefreshToken.objects.select_related('user').get(
            token=old_token_str
        )
    except RefreshToken.DoesNotExist:
        raise ValueError("Invalid refresh token")

    # Detectar reuso de refresh token (posible robo)
    if old_token.replaced_by is not None:
        # Revocar todos los refresh tokens activos del usuario
        RefreshToken.objects.filter(
            user=old_token.user,
            revoked_at__isnull=True
        ).update(revoked_at=timezone.now())
        raise ValueError("Token reuse detected")

    if not old_token.is_active():
        raise ValueError("Refresh token revoked or expired")

    # Crear nuevo refresh
    new_refresh = RefreshToken.objects.create(
        user=old_token.user,
        token=RefreshToken.generate(),
        expires_at=timezone.now() + timedelta(days=7)
    )

    # Revocar el anterior
    old_token.revoke(replaced_by=new_refresh)

    # Nuevo access token con fingerprint
    access_token = generate_access_token(old_token.user, fingerprint)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh.token
    }

def generate_refresh_token(user):
    refresh_token = RefreshToken.objects.create(
        user=user,
        token=RefreshToken.generate(),
        expires_at=timezone.now() + timedelta(days=7)
    )
    return refresh_token