from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ia_dev.application.orchestration.chat_application_service import (
    ChatApplicationService,
)
from apps.ia_dev.application.policies.policy_guard import (
    PolicyAction,
    PolicyDecision,
)


def _response(reply: str, capability_id: str) -> dict:
    domain = capability_id.split(".", 1)[0] if "." in capability_id else "attendance"
    return {
        "session_id": "sess-loop",
        "reply": reply,
        "orchestrator": {
            "intent": "attendance_query",
            "domain": domain,
            "selected_agent": "attendance_agent",
            "classifier_source": "test",
            "needs_database": True,
            "output_mode": "summary",
            "used_tools": ["attendance_analytics_trend_daily"],
        },
        "data": {
            "kpis": {"total_injustificados": 11},
            "series": [2, 3, 6],
            "labels": ["2026-04-01", "2026-04-02", "2026-04-03"],
            "insights": [],
            "table": {
                "columns": ["periodo", "total_injustificados"],
                "rows": [
                    {"periodo": "2026-04-01", "total_injustificados": 2},
                    {"periodo": "2026-04-02", "total_injustificados": 3},
                    {"periodo": "2026-04-03", "total_injustificados": 6},
                ],
                "rowcount": 3,
            },
        },
        "actions": [],
        "memory_candidates": [],
        "pending_proposals": [],
        "data_sources": {},
        "trace": [],
        "memory": {
            "used_messages": 0,
            "capacity_messages": 20,
            "usage_ratio": 0.0,
            "trim_events": 0,
            "saturated": False,
        },
        "observability": {
            "enabled": False,
            "duration_ms": 0,
            "tool_latencies_ms": {},
            "tokens_in": 0,
            "tokens_out": 0,
            "estimated_cost_usd": 0.0,
        },
        "active_nodes": [],
    }


class _FakeMemoryRuntime:
    def load_context_for_chat(self, **kwargs):
        return {
            "flags": {
                "read_enabled": True,
                "write_enabled": True,
                "proposals_enabled": True,
            },
            "decision": {"action": "read", "reason": "test"},
            "user_memory": [],
            "business_memory": [],
            "used": False,
        }

    def detect_candidates(self, **kwargs):
        return []

    def persist_candidates(self, **kwargs):
        return {
            "memory_candidates": [],
            "pending_proposals": [],
            "actions": [],
        }


class _FakePlanner:
    def __init__(self):
        self.candidates = [
            {
                "capability_id": "attendance.summary.by_supervisor.v1",
                "capability_exists": True,
                "rollout_enabled": True,
                "handler_key": "attendance.summary_by_supervisor",
                "policy_tags": ["contains_personal_data"],
                "legacy_intents": ["attendance_query"],
                "reason": "candidate_1",
                "source": {
                    "intent": "attendance_query",
                    "domain": "attendance",
                    "output_mode": "summary",
                    "needs_database": True,
                },
                "dictionary_hints": {},
                "candidate_rank": 1,
                "candidate_score": 100,
            },
            {
                "capability_id": "attendance.trend.daily.v1",
                "capability_exists": True,
                "rollout_enabled": True,
                "handler_key": "attendance.trend_daily",
                "policy_tags": ["contains_operational_data"],
                "legacy_intents": ["attendance_query"],
                "reason": "candidate_2",
                "source": {
                    "intent": "attendance_query",
                    "domain": "attendance",
                    "output_mode": "summary",
                    "needs_database": True,
                },
                "dictionary_hints": {},
                "candidate_rank": 2,
                "candidate_score": 95,
            },
        ]

    def plan_from_legacy(self, **kwargs):
        return dict(self.candidates[0])

    def plan_candidates_from_legacy(self, **kwargs):
        return [dict(item) for item in self.candidates]


class _FakePolicyGuard:
    def evaluate(self, **kwargs):
        return PolicyDecision(
            action=PolicyAction.ALLOW,
            policy_id="policy.test.allow",
            reason="test allow",
            metadata={},
        )


class _FakeBridge:
    def compare(self, **kwargs):
        planned = kwargs.get("planned_capability") or {}
        capability_id = str(planned.get("capability_id") or "")
        capability_domain = capability_id.split(".", 1)[0] if "." in capability_id else "legacy"
        return {
            "legacy_intent": "attendance_query",
            "legacy_domain": "attendance",
            "planned_capability_id": capability_id,
            "planned_capability_domain": capability_domain,
            "diverged": False,
            "reason": "test",
        }


class _FakeRouter:
    def __init__(self, *, success_on_second: bool = True):
        self.success_on_second = success_on_second
        self.execute_calls: list[str] = []

    def route(self, **kwargs):
        planned_capability = kwargs.get("planned_capability") or {}
        capability_id = str(planned_capability.get("capability_id") or "")
        return {
            "routing_mode": "capability",
            "selected_capability_id": capability_id,
            "execute_capability": True,
            "use_legacy": False,
            "shadow_enabled": True,
            "reason": "test_route",
            "policy_action": "allow",
            "policy_allowed": True,
            "capability_exists": True,
            "rollout_enabled": True,
        }

    def execute(self, **kwargs):
        planned_capability = kwargs.get("planned_capability") or {}
        capability_id = str(planned_capability.get("capability_id") or "")
        self.execute_calls.append(capability_id)
        if self.success_on_second and capability_id == "attendance.trend.daily.v1":
            return {"ok": True, "response": _response("capability second ok", capability_id)}
        return {"ok": False, "error": f"failed:{capability_id}"}


class ProactiveLoopTests(SimpleTestCase):
    def _build_service(self, *, success_on_second: bool) -> tuple[ChatApplicationService, _FakeRouter]:
        fake_router = _FakeRouter(success_on_second=success_on_second)
        service = ChatApplicationService(
            planner=_FakePlanner(),
            router=fake_router,
            bridge=_FakeBridge(),
            policy_guard=_FakePolicyGuard(),
            memory_runtime=_FakeMemoryRuntime(),
        )
        return service, fake_router

    def test_proactive_loop_executes_second_candidate_when_first_fails(self):
        with patch.dict(
            os.environ,
            {
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_PROACTIVE_LOOP_ENABLED": "1",
                "IA_DEV_PROACTIVE_LOOP_MAX_ITERATIONS": "3",
            },
            clear=False,
        ):
            service, fake_router = self._build_service(success_on_second=True)
            legacy_runner = MagicMock(side_effect=AssertionError("legacy should not be called"))
            response = service.run(
                message="dame comparativo de ausentismos",
                session_id="sess-loop-1",
                reset_memory=False,
                legacy_runner=legacy_runner,
                actor_user_key="user:loop",
            )

        self.assertEqual(response.get("reply"), "capability second ok")
        self.assertEqual(fake_router.execute_calls, ["attendance.summary.by_supervisor.v1", "attendance.trend.daily.v1"])
        legacy_runner.assert_not_called()
        loop_meta = dict(((response.get("orchestrator") or {}).get("capability_shadow") or {}).get("proactive_loop") or {})
        self.assertTrue(loop_meta.get("enabled"))
        self.assertEqual(int(loop_meta.get("iterations_ran") or 0), 2)
        self.assertFalse(bool(loop_meta.get("used_legacy")))

    def test_proactive_loop_fallbacks_to_legacy_when_all_candidates_fail(self):
        with patch.dict(
            os.environ,
            {
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_PROACTIVE_LOOP_ENABLED": "1",
                "IA_DEV_PROACTIVE_LOOP_MAX_ITERATIONS": "2",
            },
            clear=False,
        ):
            service, fake_router = self._build_service(success_on_second=False)
            legacy_runner = MagicMock(return_value=_response("legacy fallback loop", "attendance.summary.by_supervisor.v1"))
            response = service.run(
                message="dame comparativo de ausentismos",
                session_id="sess-loop-2",
                reset_memory=False,
                legacy_runner=legacy_runner,
                actor_user_key="user:loop",
            )

        self.assertEqual(response.get("reply"), "legacy fallback loop")
        self.assertEqual(fake_router.execute_calls, ["attendance.summary.by_supervisor.v1", "attendance.trend.daily.v1"])
        legacy_runner.assert_called_once()
        loop_meta = dict(((response.get("orchestrator") or {}).get("capability_shadow") or {}).get("proactive_loop") or {})
        self.assertTrue(loop_meta.get("enabled"))
        self.assertTrue(bool(loop_meta.get("used_legacy")))
