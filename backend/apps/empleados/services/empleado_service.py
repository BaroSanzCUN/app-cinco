
from apps.empleados.models import Empleado

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
    