
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ModelViewSet

from apps.operaciones.serializers.actividad_serializer import (
    ActividadSerializer,
    ActividadCreateSerializer
)
from apps.operaciones.services.actividad_service import ActividadService


class ActividadViewSet(ModelViewSet):
    # Usa permisos por defecto: IsAuthenticatedOrAPIKey

    def get_queryset(self):
        return ActividadService.listar().select_related(
            'detalle',
            'ubicacion',
            'responsable_snapshot'
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return ActividadCreateSerializer
        return ActividadSerializer

    @extend_schema(
        summary="Crear una nueva actividad",
        tags=["operaciones"],
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        actividad = ActividadService.crear(self, serializer.validated_data)

        return Response(
            ActividadSerializer(actividad).data,
            status=status.HTTP_201_CREATED
        )
