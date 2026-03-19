from django.urls import path
from apps.authentication.views import (
    LoginView,
    LegacyLoginView,
    LegacyTokenExchangeView,
    RefreshTokenView,
    LegacyRefreshTokenView,
    LogoutView,
    CsrfTokenView,
)
from apps.authentication.views.health_view import HealthCheckView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("legacy/login/", LegacyLoginView.as_view(), name="legacy-login"),
    path("legacy/exchange/", LegacyTokenExchangeView.as_view(), name="legacy-exchange"),
    path("refresh/", RefreshTokenView.as_view(), name="refresh"),
    path("legacy/refresh/", LegacyRefreshTokenView.as_view(), name="legacy-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("csrf/", CsrfTokenView.as_view(), name="csrf"),
    path("health/", HealthCheckView.as_view(), name="health"),
]
