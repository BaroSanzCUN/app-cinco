from rest_framework import serializers
from apps.empleados.models import Empleado

class EmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empleado
        # Aquí defines los campos que quieres exponer en la API
        fields = ['id', 'cedula', 'nombre', 'apellido', 'area', 'carpeta', 'cargo', 'movil', 'supervisor', 'estado', 'link_foto']
