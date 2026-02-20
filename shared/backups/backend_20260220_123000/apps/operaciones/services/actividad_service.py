from django.db import transaction
from django.utils import timezone

from apps.operaciones.models import (
    Actividad,
    ActividadDetalle,
    ActividadUbicacion,
    ActividadResponsableSnapshot
)
from apps.empleados.services import EmpleadoService

class ActividadService:

    # @staticmethod
    def crear(self, data: dict) -> Actividad:
        detalle_data = data.pop('detalle')
        ubicacion_data = data.pop('ubicacion')

        with transaction.atomic():
            # 1️⃣ Obtener empleado desde otra DB
            empleado = EmpleadoService().obtener_basico(data['responsable_id'])
            
            # datos de la sesión actual
            data['created_by'] = self.request.user.id
            data['updated_by'] = self.request.user.id
            
            actividad = Actividad.objects.create(**data)

            # 3️⃣ Snapshot del responsable
            ActividadResponsableSnapshot.objects.create(
                actividad=actividad,
                empleado_id=empleado['id'],
                nombre=empleado['nombre'],
                area=empleado['area'],
                carpeta=empleado['carpeta'],
                cargo=empleado['cargo'],
                movil=empleado['movil'],
            )

            # 4️⃣ Ubicación
            ActividadUbicacion.objects.create(
                actividad=actividad,
                **ubicacion_data
            )

            # 5️⃣ Detalle
            ActividadDetalle.objects.create(
                actividad=actividad,
                **detalle_data
            )

            return actividad

    @staticmethod
    def listar():
        return Actividad.objects.filter(is_deleted=False)
