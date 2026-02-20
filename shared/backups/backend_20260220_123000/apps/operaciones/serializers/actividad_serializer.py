from rest_framework import serializers
from apps.operaciones.models import (
    Actividad,
    ActividadDetalle,
    ActividadUbicacion
)
from apps.empleados.services import EmpleadoService


class ActividadDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActividadDetalle
        exclude = ('actividad',)


class ActividadUbicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActividadUbicacion
        exclude = ('actividad',)


class ActividadCreateSerializer(serializers.ModelSerializer):
    detalle = ActividadDetalleSerializer()
    ubicacion = ActividadUbicacionSerializer()
    
    # fecha_inicio = serializers.DateTimeField(
    #      input_formats=[
    #         "%Y-%m-%d",
    #         "%Y-%m-%dT%H:%M:%S",
    #         "%Y-%m-%dT%H:%M",
    #     ]
    # )
    
    # fecha_fin_estimado = serializers.DateTimeField(
    #     input_formats=[
    #         "%Y-%m-%d",
    #         "%Y-%m-%dT%H:%M:%S",
    #         "%Y-%m-%dT%H:%M",
    #     ]
    # )

    fecha_fin_real = serializers.DateField(
        input_formats=[
            "",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
        ],
        required=False,
        allow_null=True
    )

    class Meta:
        model = Actividad
        fields = (
            'ot',
            'responsable_id',
            'fecha_inicio',
            'fecha_fin_estimado',
            'fecha_fin_real',
            'detalle',
            'ubicacion'
        )

    def validate_responsable_id(self, value):
        if not EmpleadoService().existe(value):
            raise serializers.ValidationError("El empleado no existe.")
        return value

class ActividadSerializer(serializers.ModelSerializer):
    detalle = ActividadDetalleSerializer(read_only=True)
    ubicacion = ActividadUbicacionSerializer(read_only=True)
    responsable_snapshot = serializers.SerializerMethodField()

    class Meta:
        model = Actividad
        fields = "__all__"

    def get_responsable_snapshot(self, obj):
        if hasattr(obj, 'responsable_snapshot'):
            return {
                "nombre": obj.responsable_snapshot.nombre,
                "area": obj.responsable_snapshot.area,
                "carpeta": obj.responsable_snapshot.carpeta,
                "cargo": obj.responsable_snapshot.cargo,
                "movil": obj.responsable_snapshot.movil,
            }
        return None
