# apps/authentication/views/csrf_view.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema


class CsrfTokenView(APIView):
    """
    Endpoint para establecer la cookie CSRF.
    Debe llamarse antes de realizar requests mutantes (POST/PUT/PATCH/DELETE).
    """
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Obtener CSRF token",
        description="Establece la cookie CSRF para el frontend",
        responses={
            200: {"detail": "CSRF cookie set"},
        },
        auth=[],
    )
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"detail": "CSRF cookie set"})
