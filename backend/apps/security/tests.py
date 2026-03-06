from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock

from apps.security.services.menu_service import MenuService


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
