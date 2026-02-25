# apps/authentication/services/jwt_service.py
import jwt
from datetime import datetime, timedelta
from django.conf import settings

def generate_access_token(user, fingerprint=None):
    """
    Genera un token JWT de acceso con duración de 15 minutos.
    
    Args:
        user: Usuario autenticado
        fingerprint: Huella digital del dispositivo (opcional pero recomendado)
    
    Returns:
        str: Token JWT codificado
    """
    payload = {
        "user_id": user.id,
        "email": user.email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    
    # Agregar fingerprint si está disponible (seguridad adicional)
    if fingerprint:
        payload["fp"] = fingerprint

    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
