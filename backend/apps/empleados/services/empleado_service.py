
from apps.empleados.models import Empleado
from django.db.models import Q

class EmpleadoService:
    
    def existe(self, empleado_id):
        return Empleado.objects.filter(id=empleado_id, estado='ACTIVO').exists()
    
    # @staticmethod
    def obtener_basico(self, empleado_id):
        if not str(empleado_id).isdigit():
            return None
        
        empleado = (
            Empleado.objects
            .filter(id=empleado_id,estado='ACTIVO')
            .values('id', 'cedula', 'nombre', 'apellido', 'area', 'carpeta', 'cargo', 'movil', 'supervisor', 'estado', 'link_foto')
            .first()
        )
        
        return empleado

    @staticmethod
    def listar(query_params):
        estado = query_params.get('estado')
        if estado:
            queryset = Empleado.objects.filter(estado__iexact=estado)
        else:
            queryset = Empleado.objects.filter(estado='ACTIVO')

        filtros_icontains = {
            'cedula': 'cedula',
            'nombre': 'nombre',
            'apellido': 'apellido',
            'area': 'area',
            'carpeta': 'carpeta',
            'cargo': 'cargo',
            'movil': 'movil',
            'supervisor': 'supervisor',
            'sede': 'sede',
            'codigo_sap': 'codigo_sap',
        }

        for param, field in filtros_icontains.items():
            value = query_params.get(param)
            if value:
                queryset = queryset.filter(**{f'{field}__icontains': value})

        search = query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(cedula__icontains=search) |
                Q(nombre__icontains=search) |
                Q(apellido__icontains=search) |
                Q(cargo__icontains=search) |
                Q(movil__icontains=search)
            )

        return queryset

    @staticmethod
    def eliminar(instance: Empleado, actor_user=None, hard_delete=False) -> bool:
        if hard_delete:
            if not actor_user or not actor_user.is_authenticated or not actor_user.is_superuser:
                return False
            instance.delete()
            return True

        if instance.estado != 'INACTIVO':
            instance.estado = 'INACTIVO'
            instance.save(update_fields=['estado'])
        return True
    