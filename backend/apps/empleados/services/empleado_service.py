
from apps.empleados.models import Empleado

class EmpleadoService:
    
    def obtener_basico(empleado_id):
        # Lógica para obtener empleados
        # pass
        empleado = (
            Empleado.objects
            .filter(id=empleado_id)
            .values('id', 'cedula', 'nombre', 'apellido', 'cargo', 'movil', 'supervisor', 'link_foto')
            .first()
        )
        
        return empleado