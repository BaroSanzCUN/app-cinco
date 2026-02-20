from django.urls import path
from apps.authentication.views import LoginView, RefreshTokenView
from apps.authentication.views.health_view import HealthCheckView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
    path("health/", HealthCheckView.as_view(), name="health"),
]
