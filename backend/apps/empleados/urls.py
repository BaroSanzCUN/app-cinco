from rest_framework.routers import DefaultRouter
from apps.empleados.views import EmpleadoViewSet

router = DefaultRouter()
router.register(r'empleados', EmpleadoViewSet, basename='empleados')

urlpatterns = router.urls