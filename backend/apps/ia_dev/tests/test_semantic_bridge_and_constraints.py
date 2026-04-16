from __future__ import annotations

from dataclasses import dataclass

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    QueryExecutionPlan,
)
from apps.ia_dev.application.routing.capability_planner import CapabilityPlanner
from apps.ia_dev.application.routing.capability_router import CapabilityRouter
from apps.ia_dev.application.routing.intent_to_capability_bridge import (
    IntentToCapabilityBridge,
)


class SemanticBridgeAndConstraintsTests(SimpleTestCase):
    def test_intent_bridge_builds_semantic_candidates_from_resolved_query(self):
        bridge = IntentToCapabilityBridge()
        candidates = bridge.resolve_semantic_candidates(
            resolved_query={
                "intent": {
                    "domain_code": "ausentismo",
                    "operation": "aggregate",
                    "template_id": "aggregate_by_group_and_period",
                    "group_by": ["supervisor"],
                    "metrics": ["count"],
                },
                "normalized_filters": {},
                "normalized_period": {"label": "ultimos_6_meses"},
            },
            execution_plan={
                "strategy": "capability",
                "constraints": {"group_by": ["supervisor"]},
            },
            max_candidates=3,
        )
        self.assertTrue(candidates)
        self.assertEqual(
            str(candidates[0].get("capability_id") or ""),
            "attendance.summary.by_supervisor.v1",
        )
        self.assertEqual(
            str(candidates[0].get("reason") or ""),
            "semantic_attendance_group_supervisor",
        )

    def test_capability_planner_prioritizes_semantic_candidates(self):
        planner = CapabilityPlanner()
        candidates = planner.plan_candidates_from_legacy(
            message="consulta generica",
            classification={
                "intent": "general_question",
                "domain": "general",
                "output_mode": "summary",
                "needs_database": True,
            },
            planning_context={
                "query_intelligence": {
                    "resolved_query": {
                        "intent": {
                            "domain_code": "ausentismo",
                            "operation": "aggregate",
                            "template_id": "aggregate_by_group_and_period",
                            "group_by": ["supervisor"],
                            "metrics": ["count"],
                        },
                        "normalized_filters": {},
                        "normalized_period": {"label": "ultimos_6_meses"},
                    },
                    "execution_plan": {
                        "strategy": "capability",
                        "capability_id": "attendance.summary.by_supervisor.v1",
                        "constraints": {"group_by": ["supervisor"]},
                    },
                }
            },
            max_candidates=3,
        )
        self.assertTrue(candidates)
        self.assertEqual(
            str(candidates[0].get("capability_id") or ""),
            "attendance.summary.by_supervisor.v1",
        )
        self.assertTrue(bool(candidates[0].get("query_constraints")))

    def test_capability_router_passes_execution_constraints_to_handler(self):
        handler = _CaptureAttendanceHandler()
        router = CapabilityRouter(attendance_handler=handler)
        run_context = RunContext.create(
            message="cantidad de ausentismos por supervisor",
            session_id="sess-semantic-router",
        )
        route = {
            "execute_capability": True,
            "selected_capability_id": "attendance.summary.by_supervisor.v1",
            "reason": "test",
        }
        plan = {"capability_id": "attendance.summary.by_supervisor.v1"}
        execution_plan = QueryExecutionPlan(
            strategy="capability",
            reason="test",
            domain_code="attendance",
            capability_id="attendance.summary.by_supervisor.v1",
            constraints={
                "filters": {"cedula": "1055837370"},
                "group_by": ["supervisor"],
                "period_scope": {
                    "start_date": "2025-04-14",
                    "end_date": "2026-04-13",
                },
            },
        )
        result = router.execute(
            run_context=run_context,
            route=route,
            planned_capability=plan,
            message="cantidad de ausentismos por supervisor del ultimo año del empleado 1055837370",
            session_id="sess-semantic-router",
            reset_memory=False,
            memory_context={},
            resolved_query=None,
            execution_plan=execution_plan,
            observability=None,
        )
        self.assertTrue(bool(result.get("ok")))
        self.assertTrue(bool(result.get("meta", {}).get("constraints_applied")))
        received_plan = handler.last_kwargs.get("execution_plan")
        self.assertIsNotNone(received_plan)
        self.assertEqual(
            str((received_plan.constraints or {}).get("filters", {}).get("cedula") or ""),
            "1055837370",
        )


@dataclass
class _CaptureResult:
    ok: bool
    response: dict
    error: str | None = None
    metadata: dict | None = None


class _CaptureAttendanceHandler:
    def __init__(self):
        self.last_kwargs: dict = {}

    def handle(self, **kwargs):
        self.last_kwargs = dict(kwargs or {})
        return _CaptureResult(
            ok=True,
            response={
                "session_id": "sess-semantic-router",
                "reply": "ok",
                "orchestrator": {
                    "intent": "attendance_query",
                    "domain": "attendance",
                    "selected_agent": "attendance_agent",
                    "classifier_source": "test",
                    "needs_database": True,
                    "output_mode": "summary",
                    "used_tools": [],
                },
                "data": {
                    "kpis": {"total": 1},
                    "series": [],
                    "labels": [],
                    "insights": [],
                    "table": {"columns": [], "rows": [], "rowcount": 0},
                },
            },
            metadata={"captured": True},
        )
