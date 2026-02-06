from rest_framework import serializers

from apps.empleados.services import EmpleadoService
from apps.operaciones.models import Actividad


class ActividadSerializer(serializers.ModelSerializer):
    
    empleado = serializers.SerializerMethodField()
    
    class Meta:
        model = Actividad
        fields = "__all__"
        
    def get_empleado(self, obj):
        # pass
        return EmpleadoService().obtener_basico(obj.responsable)