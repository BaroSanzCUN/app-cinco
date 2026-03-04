from apps.empleados.models import Empleado
from rest_framework.viewsets import ModelViewSet
from apps.empleados.serializers import EmpleadoSerializer
from rest_framework import filters
from django.db.models import Q

class EmpleadoViewSet(ModelViewSet):
    queryset = Empleado.objects.all()
    serializer_class = EmpleadoSerializer
    # Usa permisos por defecto: IsAuthenticatedOrAPIKey
    filter_backends = [filters.SearchFilter]
    search_fields = ['cedula', 'nombre', 'apellido', 'cargo', 'movil']

    def get_queryset(self):
        queryset = Empleado.objects.filter(estado='ACTIVO')
        search = self.request.query_params.get('search', None)
        
        if search:
            queryset = queryset.filter(
                Q(cedula__icontains=search) |
                Q(nombre__icontains=search) |
                Q(apellido__icontains=search) |
                Q(cargo__icontains=search) |
                Q(movil__icontains=search)
            )
        
        return queryset
    
    # def 