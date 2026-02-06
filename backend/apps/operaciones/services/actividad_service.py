from apps.operaciones.models import Actividad

#1 crear una nueva actividad
#2 listar todas las actividades
#3 obtener actividades de un area específica
#4 obtener actividades de un empleado específico
#5 obtener actividades de una movil (puede abarcar varias actividades y empleados)
#6 actualizar actividad

def crear(data):
    # Lógica para crear una nueva actividad
    return Actividad.objects.create(**data)

def listar():
    # Lógica para listar todas las actividades
    return Actividad.objects.all()

def obtener_por_area(area_id):
    # Lógica para obtener actividades de un área específica
    pass
    # return ActividadModel.objects.filter(area_id=area_id)

def obtener_por_empleado(empleado_id):
    # Lógica para obtener actividades de un empleado específico
    pass
    # return ActividadModel.objects.filter(responsable=empleado_id)

# def obtener_por_movil(movil_id):
#     # Lógica para obtener actividades de una móvil específica
#     pass

def actualizar(actividad_id, data):
    # Lógica para actualizar una actividad
    pass
