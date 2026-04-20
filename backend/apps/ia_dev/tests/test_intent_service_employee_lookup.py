from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.services.intent_service import IntentClassifierService


class IntentServiceEmployeeLookupTests(SimpleTestCase):
    def test_classify_generic_employee_lookup_by_movil_identifier(self):
        service = IntentClassifierService()
        classification = service.classify("informacion de TIRAN462")
        self.assertEqual(str(classification.get("domain") or ""), "empleados")
        self.assertTrue(bool(classification.get("needs_database")))

    def test_classify_generic_employee_lookup_by_movil_identifier_without_preposition(self):
        service = IntentClassifierService()
        classification = service.classify("informacion TIRAN462")
        self.assertEqual(str(classification.get("domain") or ""), "empleados")
        self.assertTrue(bool(classification.get("needs_database")))
