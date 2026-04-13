from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.application.routing.capability_planner import CapabilityPlanner


class CapabilityPlannerCandidatesTests(SimpleTestCase):
    def test_comparative_message_prioritizes_monthly_trend(self):
        planner = CapabilityPlanner()
        candidates = planner.plan_candidates_from_legacy(
            message="Comparativo de ausentismos ultimo mes vs mes anterior con grafica",
            classification={
                "intent": "attendance_query",
                "domain": "attendance",
                "output_mode": "summary",
                "needs_database": True,
                "used_tools": [],
                "needs_personal_join": False,
                "dictionary_context": {},
            },
            planning_context={
                "memory_hints": {},
                "workflow_hints": {"pending_count": 0},
            },
            max_candidates=4,
        )
        self.assertTrue(candidates)
        self.assertEqual(candidates[0].get("capability_id"), "attendance.trend.monthly.v1")
