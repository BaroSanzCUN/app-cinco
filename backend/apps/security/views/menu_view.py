from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated

from apps.security.services.menu_service import MenuService
from apps.security.permissions.has_menu_permission import HasMenuPermission
from apps.security.serializers.menu_serializer import MenuResponseSerializer


class MenuView(APIView):
    """
    Endpoint para obtener el menú dinámico del usuario.
    Delegado a MenuService para orquestación de permisos.
    """
    permission_classes = [
        IsAuthenticated,
        HasMenuPermission,
    ]
    
    @extend_schema(
        summary="Obtener menú del usuario",
        description="Retorna el menú dinámico según los permisos del usuario autenticado",
        responses={
            200: MenuResponseSerializer,
            401: {"detail": "No se proporcionaron credenciales de autenticación."},
            403: {"detail": "No tiene permiso para realizar esta acción."},
        },
        tags=["security"],
    )
    def get(self, request):
        menu = MenuService.obtener_menu_para_usuario(request.user)
        return Response(menu)
