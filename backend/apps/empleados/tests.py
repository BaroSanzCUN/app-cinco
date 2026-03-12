from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.empleados.services.empleado_service import EmpleadoService


class EmpleadoServiceTests(TestCase):
	def test_eliminar_hard_delete_requires_superuser(self):
		instance = MagicMock()
		actor = MagicMock(is_authenticated=True, is_superuser=False)

		result = EmpleadoService.eliminar(
			instance,
			actor_user=actor,
			hard_delete=True,
		)

		self.assertFalse(result)
		instance.delete.assert_not_called()

	def test_eliminar_hard_delete_superuser(self):
		instance = MagicMock()
		actor = MagicMock(is_authenticated=True, is_superuser=True)

		result = EmpleadoService.eliminar(
			instance,
			actor_user=actor,
			hard_delete=True,
		)

		self.assertTrue(result)
		instance.delete.assert_called_once()

	def test_eliminar_soft_delete_changes_estado(self):
		instance = MagicMock(estado='ACTIVO')

		result = EmpleadoService.eliminar(
			instance,
			actor_user=None,
			hard_delete=False,
		)

		self.assertTrue(result)
		self.assertEqual(instance.estado, 'INACTIVO')
		instance.save.assert_called_once_with(update_fields=['estado'])

	@patch('apps.empleados.services.empleado_service.Empleado.objects')
	def test_listar_uses_estado_activo_when_missing(self, empleado_objects):
		queryset = MagicMock()
		empleado_objects.filter.return_value = queryset

		EmpleadoService.listar({})

		empleado_objects.filter.assert_called_once_with(estado='ACTIVO')
