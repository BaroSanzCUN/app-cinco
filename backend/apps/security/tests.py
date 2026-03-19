from django.test import TestCase
from django.contrib.auth.models import User
from django.test import override_settings
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory
from django.contrib.auth.models import AnonymousUser
from rest_framework import status
from datetime import datetime, timedelta, UTC
import jwt

from apps.authentication.services.jwt_service import generate_access_token
from apps.authentication.services.legacy_identity_service import LegacyIdentityService
from apps.security.authentication.api_key_authentication import APIKeyAuthentication
from apps.security.models import APIKey
from apps.security.services.menu_service import MenuService
from apps.authentication.views.legacy_auth_view import (
    LegacyLoginView,
    LegacyTokenExchangeView,
    LegacyRefreshTokenView,
)


class MenuServiceTestCase(TestCase):
    """
    Tests de regresión para MenuService.
    Valida que la refactorización a clase estática preserva el comportamiento.
    """

    def setUp(self):
        """Prepara usuario de prueba."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123"
        )

    @patch("apps.security.services.menu_service.ConfigMenu")
    def test_obtener_menu_filtra_por_permiso_read(self, mock_config_menu):
        """
        Verifica que solo retorna menús con permiso read=True.
        Simula ConfigMenu.objects.using("azul").filter().order_by()
        """
        # Preparar mocks de ConfigMenu
        mock_menu1 = MagicMock()
        mock_menu1.id = 1
        mock_menu1.url = "/admin/"
        mock_menu1.nombre = "Admin"
        mock_menu1.area = "Sistema"
        mock_menu1.carpeta = "Configuración"
        mock_menu1.get_permissions_for_user.return_value = {"read": True, "write": False}

        mock_menu2 = MagicMock()
        mock_menu2.id = 2
        mock_menu2.url = "/reportes/"
        mock_menu2.nombre = "Reportes"
        mock_menu2.area = "Reportes"
        mock_menu2.carpeta = None
        mock_menu2.get_permissions_for_user.return_value = {"read": False, "write": False}

        mock_menu3 = MagicMock()
        mock_menu3.id = 3
        mock_menu3.url = "/empleados/"
        mock_menu3.nombre = "Empleados"
        mock_menu3.area = "RRHH"
        mock_menu3.carpeta = "Gestión"
        mock_menu3.get_permissions_for_user.return_value = {"read": True, "write": True}

        # Configurar mock de QuerySet
        mock_config_menu.objects.using.return_value.filter.return_value.order_by.return_value = [
            mock_menu1,
            mock_menu2,
            mock_menu3,
        ]

        # Ejecutar
        resultado = MenuService.obtener_menu_para_usuario(self.user)

        # Validar: solo menús con read=True
        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0]["id"], 1)
        self.assertEqual(resultado[1]["id"], 3)
        self.assertEqual(resultado[0]["permisos"]["read"], True)
        self.assertEqual(resultado[1]["permisos"]["read"], True)

    @patch("apps.security.services.menu_service.ConfigMenu")
    def test_obtener_menu_estructura_respuesta(self, mock_config_menu):
        """
        Verifica que la estructura de respuesta incluye todos los campos necesarios.
        """
        mock_menu = MagicMock()
        mock_menu.id = 1
        mock_menu.url = "/dashboard/"
        mock_menu.nombre = "Dashboard"
        mock_menu.area = "Inicio"
        mock_menu.carpeta = "Principal"
        mock_menu.get_permissions_for_user.return_value = {"read": True, "write": False}

        mock_config_menu.objects.using.return_value.filter.return_value.order_by.return_value = [mock_menu]

        # Ejecutar
        resultado = MenuService.obtener_menu_para_usuario(self.user)

        # Validar estructura
        self.assertEqual(len(resultado), 1)
        item = resultado[0]
        self.assertIn("id", item)
        self.assertIn("url", item)
        self.assertIn("nombre", item)
        self.assertIn("area", item)
        self.assertIn("carpeta", item)
        self.assertIn("permisos", item)
        self.assertEqual(item["id"], 1)
        self.assertEqual(item["url"], "/dashboard/")

    @patch("apps.security.services.menu_service.ConfigMenu")
    def test_obtener_menu_lista_vacia_sin_permisos(self, mock_config_menu):
        """
        Verifica que retorna lista vacía cuando usuario no tiene permisos read.
        """
        mock_menu = MagicMock()
        mock_menu.get_permissions_for_user.return_value = {"read": False, "write": False}

        mock_config_menu.objects.using.return_value.filter.return_value.order_by.return_value = [mock_menu]

        # Ejecutar
        resultado = MenuService.obtener_menu_para_usuario(self.user)

        # Validar
        self.assertEqual(len(resultado), 0)
        self.assertEqual(resultado, [])

    @patch("apps.security.services.menu_service.ConfigMenu")
    def test_obtener_menu_ordena_por_area_carpeta_nombre(self, mock_config_menu):
        """
        Verifica que se consulta con order_by("area", "carpeta", "nombre").
        """
        menus_mock = MagicMock()
        mock_config_menu.objects.using.return_value.filter.return_value = menus_mock

        # Configurar retorno vacío
        menus_mock.order_by.return_value = []

        # Ejecutar
        MenuService.obtener_menu_para_usuario(self.user)

        # Validar que se llamó order_by con los parámetros correctos
        menus_mock.order_by.assert_called_once_with("area", "carpeta", "nombre")


class APIKeyAuthenticationTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.authentication = APIKeyAuthentication()
        self.user = User.objects.create_user(
            username="legacy-user",
            email="legacy@example.com",
            password="password123"
        )

        self.api_key_value, prefix, key_hash = APIKey.generate_key()
        self.api_key = APIKey.objects.create(
            name="Legacy App",
            key_hash=key_hash,
            prefix=prefix,
            is_active=True,
        )

    def test_authenticate_with_api_key_and_delegated_user_token(self):
        token = generate_access_token(self.user)
        request = self.factory.get(
            "/operaciones/actividades/",
            HTTP_X_API_KEY=self.api_key_value,
            HTTP_X_USER_TOKEN=token,
        )

        user, auth = self.authentication.authenticate(request)

        self.assertEqual(user.id, self.user.id)
        self.assertEqual(auth.id, self.api_key.id)
        self.assertEqual(request.api_key.id, self.api_key.id)
        self.assertEqual(request.delegated_user.id, self.user.id)

    def test_authenticate_with_api_key_without_user_token_returns_anonymous_user(self):
        request = self.factory.get(
            "/operaciones/actividades/",
            HTTP_X_API_KEY=self.api_key_value,
        )

        user, auth = self.authentication.authenticate(request)

        self.assertIsInstance(user, AnonymousUser)
        self.assertFalse(user.is_authenticated)
        self.assertEqual(auth.id, self.api_key.id)
        self.assertIsNone(request.delegated_user)


class LegacyAuthViewTestCase(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.api_key_value, prefix, key_hash = APIKey.generate_key()
        self.api_key = APIKey.objects.create(
            name="Legacy App",
            key_hash=key_hash,
            prefix=prefix,
            is_active=True,
        )

    @patch("apps.authentication.views.legacy_auth_view.AuthenticationService.login")
    def test_legacy_login_returns_tokens_in_body(self, mock_login):
        mock_login.return_value = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "user": {
                "id": 1,
                "username": "legacy-user",
            },
        }

        request = self.factory.post(
            "/auth/legacy/login/",
            {"username": "legacy-user", "password": "secret"},
            format="json",
            HTTP_X_API_KEY=self.api_key_value,
        )

        response = LegacyLoginView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access_token"], "access-token")
        self.assertEqual(response.data["refresh_token"], "refresh-token")
        self.assertEqual(response.data["api_client"]["id"], self.api_key.id)

    @patch("apps.authentication.views.legacy_auth_view.AuthenticationService.refresh_tokens")
    def test_legacy_refresh_returns_new_tokens_in_body(self, mock_refresh_tokens):
        mock_refresh_tokens.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
        }

        request = self.factory.post(
            "/auth/legacy/refresh/",
            {"refresh_token": "old-refresh-token"},
            format="json",
            HTTP_X_API_KEY=self.api_key_value,
        )

        response = LegacyRefreshTokenView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access_token"], "new-access-token")
        self.assertEqual(response.data["refresh_token"], "new-refresh-token")

    @override_settings(
        LEGACY_JWT_SHARED_SECRET="legacy-shared-secret",
        LEGACY_JWT_ISSUER="legacy-app",
        LEGACY_JWT_AUDIENCE="app-cinco",
        LEGACY_JWT_LEEWAY_SECONDS=30,
    )
    @patch("apps.authentication.views.legacy_auth_view.AuthenticationService.issue_tokens_for_user")
    def test_legacy_exchange_returns_backend_tokens(self, mock_issue_tokens):
        user = User.objects.create_user(
            username="exchange-user",
            email="exchange@example.com",
            password="password123"
        )
        now = datetime.now(UTC)
        legacy_token = jwt.encode(
            {
                "sub": user.username,
                "email": user.email,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=5)).timestamp()),
                "iss": "legacy-app",
                "aud": "app-cinco",
                "jti": "exchange-test-jti",
            },
            "legacy-shared-secret",
            algorithm="HS256",
        )
        mock_issue_tokens.return_value = {
            "access_token": "backend-access-token",
            "refresh_token": "backend-refresh-token",
            "user": {
                "id": user.id,
                "username": user.username,
            },
        }

        request = self.factory.post(
            "/auth/legacy/exchange/",
            {"legacy_token": legacy_token},
            format="json",
            HTTP_X_API_KEY=self.api_key_value,
        )

        response = LegacyTokenExchangeView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["access_token"], "backend-access-token")
        self.assertEqual(response.data["refresh_token"], "backend-refresh-token")


class LegacyIdentityServiceTestCase(TestCase):
    @override_settings(
        LEGACY_JWT_SHARED_SECRET="legacy-shared-secret",
        LEGACY_JWT_ISSUER="legacy-app",
        LEGACY_JWT_AUDIENCE="app-cinco",
        LEGACY_JWT_LEEWAY_SECONDS=30,
    )
    def test_exchange_legacy_token_rejects_replayed_jti(self):
        user = User.objects.create_user(
            username="legacy-replay",
            email="legacy-replay@example.com",
            password="password123"
        )
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": user.username,
                "email": user.email,
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=5)).timestamp()),
                "iss": "legacy-app",
                "aud": "app-cinco",
                "jti": "replayed-jti",
            },
            "legacy-shared-secret",
            algorithm="HS256",
        )

        resolved_user, _payload = LegacyIdentityService.exchange_legacy_token(token)
        self.assertEqual(resolved_user.id, user.id)

        with self.assertRaises(ValueError) as context:
            LegacyIdentityService.exchange_legacy_token(token)

        self.assertIn("ya fue utilizado", str(context.exception))
