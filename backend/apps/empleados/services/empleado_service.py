
from apps.empleados.models import Empleado
from django.db.models import Count, Q
from datetime import date

class EmpleadoService:
    ALLOWED_TEMPORAL_COLUMNS = {"fecha_ingreso", "fecha_egreso"}
    RESERVED_RUNTIME_PARAMS = {
        "estado",
        "search",
        "temporal_column_hint",
        "temporal_start_date",
        "temporal_end_date",
    }
    
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
        queryset = EmpleadoService._build_base_queryset(estado=query_params.get('estado'))

        filtros_icontains = {
            'cedula': 'cedula',
            'nombre': 'nombre',
            'apellido': 'apellido',
            'area': 'area',
            'carpeta': 'carpeta',
            'cargo': 'cargo',
            'tipo_labor': 'tipo_labor',
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
                Q(tipo_labor__icontains=search) |
                Q(movil__icontains=search)
            )

        temporal_column = str(query_params.get("temporal_column_hint") or "").strip().lower()
        start_date = EmpleadoService._parse_iso_date(query_params.get("temporal_start_date"))
        end_date = EmpleadoService._parse_iso_date(query_params.get("temporal_end_date"))
        if temporal_column in EmpleadoService.ALLOWED_TEMPORAL_COLUMNS and (start_date or end_date):
            if start_date:
                queryset = queryset.filter(**{f"{temporal_column}__gte": start_date})
            if end_date:
                queryset = queryset.filter(**{f"{temporal_column}__lte": end_date})

        return queryset

    @staticmethod
    def listar_runtime(query_params):
        queryset = EmpleadoService._build_base_queryset(estado=query_params.get("estado"))
        queryset = EmpleadoService._apply_runtime_filters(queryset=queryset, query_params=query_params)
        return queryset

    @staticmethod
    def contar_agrupado_runtime(*, query_params, group_by_field, limit=100):
        raw_group_fields = group_by_field if isinstance(group_by_field, (list, tuple, set)) else [group_by_field]
        group_fields = [
            EmpleadoService._resolve_model_field_name(item)
            for item in list(raw_group_fields or [])
            if str(item or "").strip()
        ]
        group_fields = [field for field in group_fields if field]
        if not group_fields:
            raise ValueError(f"campo_group_by_no_soportado:{group_by_field}")

        queryset = EmpleadoService.listar_runtime(query_params=query_params)
        safe_limit = max(1, min(int(limit), 500))
        return list(
            queryset.values(*group_fields)
            .annotate(total_empleados=Count("id"))
            .order_by("-total_empleados", *group_fields)[:safe_limit]
        )

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

    @staticmethod
    def _parse_iso_date(value) -> date | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except Exception:
            return None

    @staticmethod
    def _build_base_queryset(*, estado):
        if estado:
            return Empleado.objects.filter(estado__iexact=estado)
        return Empleado.objects.filter(estado='ACTIVO')

    @staticmethod
    def _apply_runtime_filters(*, queryset, query_params):
        for raw_key, raw_value in dict(query_params or {}).items():
            key = str(raw_key or "").strip()
            if not key or key in EmpleadoService.RESERVED_RUNTIME_PARAMS:
                continue
            if raw_value in (None, ""):
                continue
            lookup = EmpleadoService._resolve_runtime_lookup(field_name=key)
            if not lookup:
                continue
            queryset = queryset.filter(**{lookup: raw_value})

        temporal_column = str(query_params.get("temporal_column_hint") or "").strip().lower()
        start_date = EmpleadoService._parse_iso_date(query_params.get("temporal_start_date"))
        end_date = EmpleadoService._parse_iso_date(query_params.get("temporal_end_date"))
        if temporal_column in EmpleadoService.ALLOWED_TEMPORAL_COLUMNS and (start_date or end_date):
            if start_date:
                queryset = queryset.filter(**{f"{temporal_column}__gte": start_date})
            if end_date:
                queryset = queryset.filter(**{f"{temporal_column}__lte": end_date})

        return queryset

    @staticmethod
    def _resolve_runtime_lookup(*, field_name):
        field = EmpleadoService._get_model_field(field_name=field_name)
        if field is None:
            return ""
        internal_type = str(field.get_internal_type() or "")
        if internal_type in {"CharField", "TextField", "EmailField", "SlugField"}:
            return f"{field.name}__icontains"
        return field.name

    @staticmethod
    def _resolve_model_field_name(group_by_field):
        field = EmpleadoService._get_model_field(field_name=group_by_field)
        return str(field.name or "") if field is not None else ""

    @staticmethod
    def _get_model_field(*, field_name):
        clean = str(field_name or "").strip()
        if not clean:
            return None
        try:
            return Empleado._meta.get_field(clean)
        except Exception:
            return None
    
