from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.services.orchestrator_service import IADevOrchestratorService


class OrchestratorLegacySemanticsTests(SimpleTestCase):
    def setUp(self):
        # Evitamos inicializacion completa (tools/servicios externos) para testear helpers puros.
        self.service = IADevOrchestratorService.__new__(IADevOrchestratorService)

    def test_group_dimension_resolves_area_from_plural_question(self):
        resolved = self.service._resolve_attendance_group_dimension(
            "Que areas concentran mas ausentismos en rolling 90 dias"
        )
        self.assertEqual(resolved, ("area", "Area"))

    def test_group_aggregate_detects_concentration_without_count_tokens(self):
        should_aggregate = self.service._is_attendance_group_count_request(
            message="Que areas concentran mas ausentismos en rolling 90 dias",
            group_dimension=("area", "Area"),
        )
        self.assertTrue(should_aggregate)

    def test_probable_causes_request_detection(self):
        self.assertTrue(
            self.service._message_requests_probable_causes(
                "Que areas concentran mas ausentismos y que causas probables sugieres"
            )
        )

    def test_generate_probable_causes_returns_heuristic_meta_when_service_unavailable(self):
        result = self.service._generate_probable_causes(
            message="Que areas concentran mas ausentismos",
            rows=[
                {"area": "I&M", "total_ausentismos": 366, "porcentaje": 73.2},
                {"area": "IMPLEMENTACION FO", "total_ausentismos": 51, "porcentaje": 10.2},
            ],
            group_label="Area",
            metric_key="total_ausentismos",
        )
        meta = dict(result.get("meta") or {})
        self.assertEqual(str(meta.get("generator") or ""), "heuristic")
        self.assertEqual(str(meta.get("top_group") or ""), "I&M")
        self.assertAlmostEqual(float(meta.get("top_pct") or 0.0), 73.2, places=1)
        self.assertTrue(str(meta.get("prompt_hash") or ""))
        self.assertIsInstance(meta.get("validation_errors"), list)
        self.assertIsInstance(meta.get("policy_decision"), dict)
        self.assertTrue(list(result.get("insights") or []))

    def test_generate_probable_causes_uses_injected_diagnostics_service(self):
        class _FakeDiagnosticsService:
            def generate(self, **kwargs):
                return {
                    "insights": ["Hallazgo validado por evidencia."],
                    "meta": {
                        "generator": "openai",
                        "evidence_rows": [{"group": "I&M", "count": 366, "pct": 73.2}],
                        "top_group": "I&M",
                        "top_pct": 73.2,
                        "confidence": 0.88,
                        "validated": True,
                    },
                }

        self.service.cause_diagnostics_service = _FakeDiagnosticsService()
        result = self.service._generate_probable_causes(
            message="Que areas concentran mas ausentismos y que causas sugieres",
            rows=[{"area": "I&M", "total_ausentismos": 366, "porcentaje": 73.2}],
            group_label="Area",
            metric_key="total_ausentismos",
        )
        meta = dict(result.get("meta") or {})
        self.assertEqual(str(meta.get("generator") or ""), "openai")
        self.assertTrue(bool(meta.get("validated")))
        self.assertTrue(list(result.get("insights") or []))
