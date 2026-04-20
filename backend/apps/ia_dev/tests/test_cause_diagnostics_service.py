from __future__ import annotations

import os
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ia_dev.application.semantic.cause_diagnostics_service import (
    CauseDiagnosticsService,
)


class CauseDiagnosticsServiceTests(SimpleTestCase):
    def setUp(self):
        self.rows = [
            {"area": "I&M", "total_ausentismos": 366, "porcentaje": 73.2},
            {"area": "IMPLEMENTACION FO", "total_ausentismos": 51, "porcentaje": 10.2},
        ]

    class _ObservabilityStub:
        def __init__(self):
            self.events: list[dict] = []

        def record_event(self, *, event_type: str, source: str, meta: dict):
            self.events.append(
                {
                    "event_type": event_type,
                    "source": source,
                    "meta": dict(meta or {}),
                }
            )

    def test_generate_uses_heuristic_when_openai_disabled(self):
        service = CauseDiagnosticsService()
        with patch.dict(
            os.environ,
            {
                "IA_DEV_CAUSE_DIAGNOSTICS_ENABLED": "1",
                "IA_DEV_CAUSE_DIAGNOSTICS_OPENAI_ENABLED": "0",
            },
            clear=False,
        ):
            result = service.generate(
                message="Que areas concentran mas ausentismos y que causas sugieres",
                rows=self.rows,
                group_label="Area",
                metric_key="total_ausentismos",
            )
        meta = dict(result.get("meta") or {})
        self.assertEqual(str(meta.get("generator") or ""), "heuristic")
        self.assertEqual(str(meta.get("top_group") or ""), "I&M")
        self.assertEqual(float(meta.get("top_pct") or 0.0), 73.2)
        self.assertTrue(str(meta.get("prompt_hash") or ""))
        self.assertIsInstance(meta.get("validation_errors"), list)
        self.assertIsInstance(meta.get("policy_decision"), dict)
        self.assertEqual(str((meta.get("policy_decision") or {}).get("selected_generator") or ""), "heuristic")
        self.assertTrue(list(result.get("insights") or []))

    def test_generate_fallbacks_to_heuristic_when_openai_payload_invalid(self):
        service = CauseDiagnosticsService()
        with patch.dict(
            os.environ,
            {
                "IA_DEV_CAUSE_DIAGNOSTICS_ENABLED": "1",
                "IA_DEV_CAUSE_DIAGNOSTICS_OPENAI_ENABLED": "1",
            },
            clear=False,
        ):
            with patch.object(CauseDiagnosticsService, "_get_openai_api_key", return_value="dummy"):
                with patch.object(service, "_generate_openai_payload", return_value={"diagnostics": [], "confidence": 0.99}):
                    result = service.generate(
                        message="Que areas concentran mas ausentismos y que causas sugieres",
                        rows=self.rows,
                        group_label="Area",
                        metric_key="total_ausentismos",
                    )
        meta = dict(result.get("meta") or {})
        self.assertEqual(str(meta.get("generator") or ""), "heuristic")
        self.assertIn("openai_payload_invalid", str(meta.get("fallback_reason") or ""))
        self.assertTrue(bool(list(meta.get("validation_errors") or [])))
        self.assertEqual(str((meta.get("policy_decision") or {}).get("selected_generator") or ""), "heuristic")
        self.assertTrue(list(result.get("insights") or []))

    def test_generate_accepts_valid_openai_payload(self):
        service = CauseDiagnosticsService()
        payload = {
            "diagnostics": [
                {
                    "finding": "La mayor presion se observa en I&M",
                    "suggestion": "Revisar cobertura por turno y ausencias medicas",
                    "evidence_groups": ["I&M"],
                    "confidence": 0.85,
                }
            ],
            "confidence": 0.82,
        }
        with patch.dict(
            os.environ,
            {
                "IA_DEV_CAUSE_DIAGNOSTICS_ENABLED": "1",
                "IA_DEV_CAUSE_DIAGNOSTICS_OPENAI_ENABLED": "1",
                "IA_DEV_CAUSE_DIAGNOSTICS_MIN_CONFIDENCE": "0.60",
            },
            clear=False,
        ):
            with patch.object(CauseDiagnosticsService, "_get_openai_api_key", return_value="dummy"):
                with patch.object(service, "_generate_openai_payload", return_value=payload):
                    result = service.generate(
                        message="Que areas concentran mas ausentismos y que causas sugieres",
                        rows=self.rows,
                        group_label="Area",
                        metric_key="total_ausentismos",
                    )
        meta = dict(result.get("meta") or {})
        self.assertEqual(str(meta.get("generator") or ""), "openai")
        self.assertTrue(bool(meta.get("validated")))
        self.assertEqual(list(meta.get("validation_errors") or []), [])
        self.assertEqual(str((meta.get("policy_decision") or {}).get("selected_generator") or ""), "openai")
        self.assertTrue(any("evidencia" in str(item).lower() for item in list(result.get("insights") or [])))

    def test_generate_records_cause_diagnostics_result_event(self):
        service = CauseDiagnosticsService()
        observability = self._ObservabilityStub()
        with patch.dict(
            os.environ,
            {
                "IA_DEV_CAUSE_DIAGNOSTICS_ENABLED": "1",
                "IA_DEV_CAUSE_DIAGNOSTICS_OPENAI_ENABLED": "0",
            },
            clear=False,
        ):
            service.generate(
                message="Que areas concentran mas ausentismos y que causas sugieres",
                rows=self.rows,
                group_label="Area",
                metric_key="total_ausentismos",
                observability=observability,
                run_id="run-test-001",
                trace_id="trace-test-001",
                domain_code="attendance",
                capability_id="attendance.summary.by_area.v1",
            )
        result_events = [item for item in observability.events if item.get("event_type") == "cause_diagnostics_result"]
        self.assertTrue(bool(result_events))
        meta = dict(result_events[0].get("meta") or {})
        self.assertEqual(str(meta.get("domain_code") or ""), "attendance")
        self.assertEqual(str(meta.get("capability_id") or ""), "attendance.summary.by_area.v1")
        self.assertEqual(str(meta.get("generator") or ""), "heuristic")
