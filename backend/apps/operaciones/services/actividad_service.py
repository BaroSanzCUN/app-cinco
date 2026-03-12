from django.db import transaction
from django.utils import timezone

from apps.operaciones.models import (
    Actividad,
    ActividadDetalle,
    ActividadUbicacion,
    ActividadResponsableSnapshot
)
from apps.empleados.services import EmpleadoService
from django.db.models import Q

class ActividadService:

    @staticmethod
    def crear(data: dict, actor_user_id=None) -> Actividad:
        payload = data.copy()
        detalle_data = payload.pop('detalle')
        ubicacion_data = payload.pop('ubicacion')

        with transaction.atomic():
            empleado = EmpleadoService().obtener_basico(payload['responsable_id'])

            payload['created_by'] = actor_user_id
            payload['updated_by'] = actor_user_id

            actividad = Actividad.objects.create(**payload)

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
    def listar(usuario_id=None, filtros=None):
        queryset = Actividad.objects.filter(is_deleted=False).select_related(
            'detalle',
            'ubicacion',
            'responsable_snapshot'
        )
        filtros = filtros or {}

        if usuario_id:
            queryset = queryset.filter(
                Q(created_by=usuario_id) |
                Q(responsable_snapshot__empleado_id=usuario_id)
            ).distinct()

        if filtros.get('ot'):
            queryset = queryset.filter(ot__icontains=filtros['ot'])

        if filtros.get('estado'):
            queryset = queryset.filter(estado=filtros['estado'])

        if filtros.get('area'):
            queryset = queryset.filter(
                responsable_snapshot__area__icontains=filtros['area']
            )

        if filtros.get('carpeta'):
            queryset = queryset.filter(
                responsable_snapshot__carpeta__icontains=filtros['carpeta']
            )

        if filtros.get('buscar'):
            buscar = filtros['buscar']
            queryset = queryset.filter(
                Q(detalle__descripcion__icontains=buscar) |
                Q(detalle__tipo_trabajo__icontains=buscar) |
                Q(ot__icontains=buscar) |
                Q(responsable_snapshot__nombre__icontains=buscar)
            ).distinct()

        if filtros.get('responsable_id'):
            queryset = queryset.filter(
                responsable_snapshot__empleado_id=filtros['responsable_id']
            )

        if filtros.get('fecha_inicio_desde'):
            queryset = queryset.filter(
                fecha_inicio__gte=filtros['fecha_inicio_desde']
            )

        if filtros.get('fecha_inicio_hasta'):
            queryset = queryset.filter(
                fecha_inicio__lte=filtros['fecha_inicio_hasta']
            )

        if filtros.get('zona'):
            queryset = queryset.filter(
                ubicacion__zona__icontains=filtros['zona']
            )

        if filtros.get('nodo'):
            queryset = queryset.filter(
                ubicacion__nodo__icontains=filtros['nodo']
            )

        return queryset

    @staticmethod
    def eliminar(instance: Actividad, actor_user=None, hard_delete=False) -> bool:
        if hard_delete:
            if not actor_user or not actor_user.is_authenticated or not actor_user.is_superuser:
                return False
            instance.delete()
            return True

        deleted_by = actor_user.id if actor_user and actor_user.is_authenticated else None
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.deleted_by = deleted_by
        instance.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'updated_at'])
        return True
