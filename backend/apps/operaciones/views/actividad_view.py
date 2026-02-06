

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.operaciones.services import crear

class ActividadesView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    # permission_classes = []
    
    ## Crear endpoints para:
    #1 crear una nueva actividad
    #2 listar todas las actividades
    #3 obtener actividades de un area específica
    #4 obtener actividades de un empleado específico
    #5 obtener actividades de una movil (puede abarcar varias actividades y empleados)
    #6 actualizar el estado de una actividad
    
    
    # 1 Crear una nueva actividad
    def create(self, request):
        data = request.data
        nueva_actividad = crear(data)
        return Response({"actividad": nueva_actividad.id}, status=201)
    