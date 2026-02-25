from django.urls import path
from apps.authentication.views import LoginView, RefreshTokenView, LogoutView, CsrfTokenView
from apps.authentication.views.health_view import HealthCheckView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("csrf/", CsrfTokenView.as_view(), name="csrf"),
    path("health/", HealthCheckView.as_view(), name="health"),
]
