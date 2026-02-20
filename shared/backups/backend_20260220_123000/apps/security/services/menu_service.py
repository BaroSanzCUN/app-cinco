from apps.common.models import ConfigMenu

def build_menu_for_user(user):
    menus = ConfigMenu.objects.using("azul").filter(estado="ACTIVO").order_by("area", "carpeta", "nombre")

    response = []

    for menu in menus:
        permisos = menu.get_permissions_for_user(user, menu.url)

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
