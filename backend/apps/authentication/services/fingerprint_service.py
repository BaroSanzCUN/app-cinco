# apps/authentication/services/fingerprint_service.py
import hashlib


def get_device_fingerprint(request):
    """
    Genera una huella digital del dispositivo basada en:
    - User-Agent: Navegador y sistema operativo
    - Accept-Language: Preferencias de idioma
    
    Nota: No usamos IP para evitar falsos positivos en redes móviles.
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    
    # Combinar y generar hash (sin IP para evitar rotaciones en redes moviles)
    fingerprint_string = f"{user_agent}|{accept_language}"
    fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    # Retornar solo los primeros 16 caracteres para mantener el token compacto
    return fingerprint_hash[:16]


def validate_device_fingerprint(request, token_fingerprint):
    """
    Valida que el fingerprint del request coincida con el del token.
    
    Returns:
        bool: True si coinciden, False si no
    """
    current_fingerprint = get_device_fingerprint(request)
    return current_fingerprint == token_fingerprint
