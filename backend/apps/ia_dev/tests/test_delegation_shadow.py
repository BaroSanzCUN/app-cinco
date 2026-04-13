from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.delegation.delegation_coordinator import (
    DelegationCoordinator,
)
from apps.ia_dev.application.delegation.task_planner import TaskPlanner


class DelegationShadowModeTests(SimpleTestCase):
    def test_task_planner_generates_ausentismo_tasks_for_analytics_query(self):
        planner = TaskPlanner()
        plan = planner.plan_tasks(
            message="comparame ausentismo por supervisor, muestralo en grafica",
            classification={
                "intent": "attendance_query",
                "domain": "attendance",
                "selected_agent": "attendance_agent",
                "needs_database": True,
                "output_mode": "summary",
            },
            planned_candidates=[
                {
                    "capability_id": "attendance.summary.by_supervisor.v1",
                    "reason": "semantic",
                }
            ],
            run_id="run_test_001",
            trace_id="trace_test_001",
        )

        self.assertTrue(bool(plan.get("should_delegate")))
        tasks = list(plan.get("tasks") or [])
        self.assertGreaterEqual(len(tasks), 3)
        self.assertTrue(any(item.task_type == "resumen_supervisor" for item in tasks))
        self.assertTrue(any(item.task_type == "tabla_supervisor" for item in tasks))
        self.assertTrue(any(item.task_type in {"tendencia_mensual", "tendencia_diaria"} for item in tasks))

    def test_delegation_coordinator_shadow_does_not_execute(self):
        coordinator = DelegationCoordinator()
        run_context = RunContext.create(message="comparame ausentismo por supervisor")
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_DELEGATION_ENABLED": "1",
                "IA_DEV_DELEGATION_MODE": "shadow",
            },
            clear=False,
        ):
            decision = coordinator.plan_and_maybe_execute(
                message="comparame ausentismo por supervisor, muestralo en grafica",
                classification={
                    "intent": "attendance_query",
                    "domain": "attendance",
                    "selected_agent": "attendance_agent",
                    "needs_database": True,
                    "output_mode": "summary",
                },
                planned_candidates=[
                    {
                        "capability_id": "attendance.summary.by_supervisor.v1",
                        "reason": "semantic",
                    }
                ],
                run_context=run_context,
                observability=None,
            )

        self.assertEqual(str(decision.get("mode") or ""), "shadow")
        self.assertTrue(bool(decision.get("should_delegate")))
        self.assertFalse(bool(decision.get("executed")))
        self.assertFalse(bool(decision.get("response")))
        tasks = list(decision.get("tasks") or [])
        self.assertGreaterEqual(len(tasks), 3)
