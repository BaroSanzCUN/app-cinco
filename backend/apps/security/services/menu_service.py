from apps.common.models import ConfigMenu


class MenuService:
    """
    Servicio para gestionar menú dinámico del usuario.
    Encapsula queries y lógica de permisos.
    """

    @staticmethod
    def obtener_menu_para_usuario(user):
        """
        Construye el menú dinámico del usuario filtrando por permisos.
        
        Args:
            user: Usuario autenticado
            
        Returns:
            Lista de items de menú con permisos asociados
        """
        menus = ConfigMenu.objects.using("azul").filter(
            estado="ACTIVO"
        ).order_by("area", "carpeta", "nombre")

        response = []

        for menu in menus:
            permisos = menu.get_permissions_for_user(user, menu.url)

            # Filtrar solo menús que el usuario puede leer
            if not permisos.get("read", False):
                continue

            response.append({
                "id": menu.id,
                "url": menu.url,
                "nombre": menu.nombre,
                "area": menu.area,
                "carpeta": menu.carpeta,
                "permisos": permisos,
            })

        return response


# Compatibilidad hacia atrás
def build_menu_for_user(user):
    """Función legada para compatibilidad."""
    return MenuService.obtener_menu_para_usuario(user)
