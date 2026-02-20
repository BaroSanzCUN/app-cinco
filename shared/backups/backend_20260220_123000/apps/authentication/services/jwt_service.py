# apps/authentication/services/jwt_service.py
import jwt
from datetime import datetime, timedelta
from django.conf import settings

def generate_access_token(user):
    payload = {
        "user_id": user.id,
        "email": user.email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
