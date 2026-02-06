# from encodings.punycode import T
from django.db import models
from django.utils import timezone

class Actividad(models.Model):
    """Modelo para gestionar actividades operacionales"""
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    
    id = models.AutoField(primary_key=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    # responsable -> empleado asignado (relacionar)
    responsable = models.CharField(max_length=100, blank=True, null=True)
    ot = models.CharField(max_length=100, unique=True, null=True)
    direccion = models.CharField(max_length=255, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    # 
    zona = models.CharField(max_length=100, blank=True, null=True)
    # 
    nodo = models.CharField(max_length=100, blank=True, null=True)
    fin_estimado = models.DateTimeField(blank=True, null=True)
    fin_real = models.DateTimeField(blank=True, null=True)
    # edit -> updated_by (relacionar)
    edit = models.CharField(max_length=100, blank=True, null=True)
    # fecha_edit -> updated_at 
    fecha_edit = models.DateTimeField(blank=True, null=True)
    
    # relacion de responsable y edit con modelo Empleado
    
    
    class Meta:
        db_table = 'operaciones_actividades'
        app_label = 'operaciones'
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['-id']
    