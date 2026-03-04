from rest_framework.permissions import BasePermission
from apps.security.models import APIKey


class IsAuthenticatedOrAPIKey(BasePermission):
    """
    Permite acceso a usuarios autenticados vía JWT o aplicaciones con API Key válida
    """
    def has_permission(self, request, view):
        # Si es un usuario autenticado (JWT)
        if request.user and request.user.is_authenticated:
            return True
        
        # Si es una aplicación con API Key válida
        if request.auth and isinstance(request.auth, APIKey):
            return True
        
        return False


class IsUserOnly(BasePermission):
    """
    Solo permite acceso a usuarios autenticados, NO a API Keys
    Útil para endpoints que requieren contexto de usuario
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsAPIKeyOnly(BasePermission):
    """
    Solo permite acceso a aplicaciones con API Key, NO a usuarios
    Útil para endpoints específicos de integración
    """
    def has_permission(self, request, view):
        return request.auth and isinstance(request.auth, APIKey)


class IsAuthenticatedUser(BasePermission):
    """
    Permiso estricto: solo usuarios autenticados
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
