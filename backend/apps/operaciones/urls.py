from rest_framework.routers import DefaultRouter
from apps.operaciones.views import ActividadViewSet

router = DefaultRouter()
router.register(r'actividades', ActividadViewSet, basename='actividades')

urlpatterns = router.urls