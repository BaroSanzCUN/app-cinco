from rest_framework.permissions import BasePermission

class HasMenuPermission(BasePermission):
    """
    Permiso base para endpoints de seguridad.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Aquí puedes agregar reglas globales si luego lo necesitas
        return True
