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

    def test_resolve_candidates_maps_grouped_employee_summary_without_explicit_count(self):
        candidates = self.bridge.resolve_candidates(
            message="empleados por area",
            classification={
                "intent": "employee_query",
                "domain": "empleados",
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

    def test_resolve_prefers_attendance_by_area_for_simple_grouped_summary(self):
        planned = self.bridge.resolve(
            message="ausentismos por area",
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

    def test_resolve_semantic_candidates_maps_grouped_employee_query_with_estado_empleado(self):
        candidates = self.bridge.resolve_semantic_candidates(
            resolved_query={
                "intent": {
                    "domain_code": "empleados",
                    "template_id": "aggregate_by_group_and_period",
                    "operation": "aggregate",
                    "group_by": ["area"],
                    "metrics": ["count"],
                },
                "normalized_filters": {"estado_empleado": "ACTIVO"},
                "normalized_period": {},
            },
            execution_plan={},
            max_candidates=4,
        )
        capability_ids = [str(item.get("capability_id") or "") for item in candidates]
        self.assertIn("empleados.count.active.v1", capability_ids)
