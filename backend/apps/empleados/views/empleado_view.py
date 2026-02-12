from apps.empleados.models import Empleado
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ModelViewSet
from apps.empleados.serializers import EmpleadoSerializer

class EmpleadoViewSet(ModelViewSet):
    queryset = Empleado.objects.all()
    serializer_class = EmpleadoSerializer
    permission_classes = [AllowAny]


    def get_queryset(self):
        return Empleado.objects.filter(estado='ACTIVO')
    
    # def 