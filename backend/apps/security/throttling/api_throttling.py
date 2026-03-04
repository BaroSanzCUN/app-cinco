from rest_framework.throttling import BaseThrottle
from django.core.cache import cache
from django.utils import timezone
from apps.security.models import APIKey
from rest_framework.exceptions import Throttled


class APIKeyRateThrottle(BaseThrottle):
    """
    Rate limiting basado en el límite configurado en cada API Key
    """
    
    def allow_request(self, request, view):
        # Solo aplicar throttling a requests con API Key
        if not isinstance(request.auth, APIKey):
            return True
        
        api_key = request.auth
        
        # Obtener el límite de rate configurado
        rate_limit = api_key.rate_limit
        
        # Clave única para este API Key en cache
        cache_key = f"throttle_apikey_{api_key.id}"
        
        # Obtener el contador actual
        now = timezone.now()
        history = cache.get(cache_key, [])
        
        # Filtrar requests de la última hora
        cutoff = now.timestamp() - 3600  # 1 hora
        history = [timestamp for timestamp in history if timestamp > cutoff]
        
        # Verificar si excede el límite
        if len(history) >= rate_limit:
            # Calcular tiempo de espera
            wait = 3600 - (now.timestamp() - history[0])
            raise Throttled(wait=wait, detail=f"Rate limit excedido. Límite: {rate_limit} requests/hora")
        
        # Agregar este request al historial
        history.append(now.timestamp())
        cache.set(cache_key, history, 3600)  # Expira en 1 hora
        
        return True

    def wait(self):
        """
        Opcionalmente retorna el tiempo de espera en segundos
        """
        return None
