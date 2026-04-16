from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.application.routing.intent_to_capability_bridge import (
    IntentToCapabilityBridge,
)


class SemanticBridgeCandidateTests(SimpleTestCase):
    def setUp(self):
        self.bridge = IntentToCapabilityBridge()

    def test_resolve_candidates_includes_comparative_trend_fallbacks(self):
        candidates = self.bridge.resolve_candidates(
            message="Dame comparativo de ausentismos, ultimo mes vs mes anterior con grafica",
            classification={
                "intent": "attendance_query",
                "domain": "attendance",
                "output_mode": "summary",
                "needs_database": True,
                "used_tools": [],
                "needs_personal_join": False,
            },
            max_candidates=4,
        )
        capability_ids = [str(item.get("capability_id") or "") for item in candidates]
        self.assertIn("attendance.trend.monthly.v1", capability_ids)
        self.assertIn("attendance.trend.daily.v1", capability_ids)

    def test_resolve_candidates_recovers_attendance_from_general_semantics(self):
        candidates = self.bridge.resolve_candidates(
            message="grafica de ausentismos por supervisor",
            classification={
                "intent": "general_question",
                "domain": "general",
                "output_mode": "summary",
                "needs_database": True,
                "used_tools": [],
                "needs_personal_join": False,
            },
            max_candidates=4,
        )
        capability_ids = [str(item.get("capability_id") or "") for item in candidates]
        self.assertIn("attendance.summary.by_supervisor.v1", capability_ids)

    def test_resolve_candidates_maps_active_employee_count(self):
        candidates = self.bridge.resolve_candidates(
            message="Cantidad empleados activos",
            classification={
                "intent": "employee_query",
                "domain": "rrhh",
                "output_mode": "summary",
                "needs_database": True,
                "used_tools": [],
                "needs_personal_join": False,
            },
            max_candidates=4,
        )
        capability_ids = [str(item.get("capability_id") or "") for item in candidates]
        self.assertIn("empleados.count.active.v1", capability_ids)

    def test_resolve_candidates_maps_attendance_group_attribute(self):
        candidates = self.bridge.resolve_candidates(
            message="Cantidad de ausentismos por carpeta en los ultimos 15 dias",
            classification={
                "intent": "attendance_query",
                "domain": "attendance",
                "output_mode": "summary",
                "needs_database": True,
                "used_tools": [],
                "needs_personal_join": True,
            },
            max_candidates=4,
        )
        capability_ids = [str(item.get("capability_id") or "") for item in candidates]
        self.assertIn("attendance.summary.by_attribute.v1", capability_ids)

    def test_resolve_prefers_area_summary_for_concentration_question_without_por_area(self):
        planned = self.bridge.resolve(
            message="Que areas concentran mas ausentismos en rolling 90 dias y que causas probables sugieres",
            classification={
                "intent": "attendance_query",
                "domain": "attendance",
                "output_mode": "summary",
                "needs_database": True,
                "used_tools": [],
                "needs_personal_join": False,
            },
        )
        self.assertEqual(str(planned.get("capability_id") or ""), "attendance.summary.by_area.v1")
