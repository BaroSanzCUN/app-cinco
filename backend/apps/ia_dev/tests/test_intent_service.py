from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ia_dev.services.intent_service import IntentClassifierService


class IntentClassifierServiceTests(SimpleTestCase):
    def test_rules_classifier_maps_vigentes_count_to_empleados(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_USE_OPENAI_CLASSIFIER": "0",
            },
            clear=False,
        ):
            service = IntentClassifierService()
            result = service.classify("cuántos vigentes hay")
        self.assertEqual(str(result.get("domain") or ""), "empleados")
        self.assertEqual(str(result.get("intent") or ""), "employee_query")
        self.assertTrue(bool(result.get("needs_database")))
        self.assertEqual(str(result.get("selected_agent") or ""), "empleados_agent")

    def test_rules_classifier_maps_status_with_hay_to_empleados(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_USE_OPENAI_CLASSIFIER": "0",
            },
            clear=False,
        ):
            service = IntentClassifierService()
            result = service.classify("vigentes hay")
        self.assertEqual(str(result.get("domain") or ""), "empleados")
        self.assertEqual(str(result.get("intent") or ""), "employee_query")

    def test_openai_misclassification_is_corrected_by_deterministic_override(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_USE_OPENAI_CLASSIFIER": "1",
                "OPENAI_API_KEY": "test-key",
            },
            clear=False,
        ):
            service = IntentClassifierService()
            service._classify_openai = lambda *_args, **_kwargs: {  # type: ignore[method-assign]
                "domain": "general",
                "intent": "knowledge_request",
                "selected_agent": "analista_agent",
                "needs_database": False,
                "output_mode": "summary",
            }
            result = service.classify("cuántos vigentes hay")
        self.assertEqual(str(result.get("domain") or ""), "empleados")
        self.assertEqual(str(result.get("intent") or ""), "employee_query")
        self.assertEqual(str(result.get("selected_agent") or ""), "empleados_agent")
