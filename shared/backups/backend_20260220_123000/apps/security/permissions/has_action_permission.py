from rest_framework.permissions import BasePermission
from apps.common.models import ConfigMenu


class HasMenuActionPermission(BasePermission):
    """
    Valida permisos por acción para un módulo específico.
    """

    action_required = None  # 'read', 'edit', 'insert', etc.

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        menu_code = getattr(view, "menu_code", None)
        if not menu_code:
            # Endpoint sin control de menú
            return True

        if not self.action_required:
            return False

        menu = ConfigMenu.objects.filter(codigo=menu_code).first()
        if not menu:
            return False

        permisos = menu.get_permissions_for_user(request.user)
        return permisos.get(self.action_required, False)
