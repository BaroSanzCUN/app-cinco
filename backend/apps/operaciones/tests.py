from unittest import TestCase
from unittest.mock import MagicMock, patch

from apps.operaciones.services.actividad_service import ActividadService


class ActividadServiceTests(TestCase):
	def test_eliminar_hard_delete_requires_superuser(self):
		instance = MagicMock()
		actor = MagicMock(is_authenticated=True, is_superuser=False)

		result = ActividadService.eliminar(
			instance,
			actor_user=actor,
			hard_delete=True,
		)

		self.assertFalse(result)
		instance.delete.assert_not_called()

	def test_eliminar_hard_delete_superuser(self):
		instance = MagicMock()
		actor = MagicMock(is_authenticated=True, is_superuser=True)

		result = ActividadService.eliminar(
			instance,
			actor_user=actor,
			hard_delete=True,
		)

		self.assertTrue(result)
		instance.delete.assert_called_once()

	def test_eliminar_soft_delete_marks_flags(self):
		instance = MagicMock()
		actor = MagicMock(is_authenticated=True, id=99)

		result = ActividadService.eliminar(
			instance,
			actor_user=actor,
			hard_delete=False,
		)

		self.assertTrue(result)
		self.assertTrue(instance.is_deleted)
		self.assertEqual(instance.deleted_by, 99)
		instance.save.assert_called_once_with(
			update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'updated_at']
		)

	@patch('apps.operaciones.services.actividad_service.Actividad.objects')
	def test_listar_applies_default_base_filter(self, actividad_objects):
		queryset = MagicMock()
		queryset.select_related.return_value = queryset
		actividad_objects.filter.return_value = queryset

		ActividadService.listar(usuario_id=None, filtros={})

		actividad_objects.filter.assert_called_once_with(is_deleted=False)
		queryset.select_related.assert_called_once_with(
			'detalle',
			'ubicacion',
			'responsable_snapshot'
		)
