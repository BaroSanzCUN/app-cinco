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
from apps.ia_dev.application.routing.capability_catalog import CapabilityCatalog


def _response(reply: str, capability_id: str) -> dict:
    domain = capability_id.split(".", 1)[0] if "." in capability_id else "general"
    return {
        "session_id": "sess-loop-controller",
        "reply": reply,
        "orchestrator": {
            "intent": "attendance_query" if domain == "attendance" else "general_question",
            "domain": domain,
            "selected_agent": "attendance_agent" if domain == "attendance" else "analista_agent",
            "classifier_source": "test",
            "needs_database": domain not in {"general", "legacy"},
            "output_mode": "summary",
            "used_tools": [],
        },
        "data": {
            "kpis": {"total": 10},
            "series": [],
            "labels": [],
            "insights": [],
            "table": {"columns": ["total"], "rows": [{"total": 10}], "rowcount": 1},
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


def _build_plan(capability_id: str, *, rank: int, score: int) -> dict:
    catalog = CapabilityCatalog()
    definition = catalog.get(capability_id)
    domain = capability_id.split(".", 1)[0] if "." in capability_id else "general"
    return {
        "capability_id": capability_id,
        "capability_exists": bool(definition),
        "rollout_enabled": True,
        "handler_key": definition.handler_key if definition else "legacy.passthrough",
        "policy_tags": list(definition.policy_tags) if definition else [],
        "legacy_intents": list(definition.legacy_intents) if definition else [],
        "reason": f"candidate_{rank}",
        "source": {
            "intent": "attendance_query",
            "domain": domain,
            "output_mode": "summary",
            "needs_database": True,
        },
        "dictionary_hints": {},
        "candidate_rank": rank,
        "candidate_score": score,
    }


class _FakePlanner:
    def __init__(self):
        self.candidates = [
            _build_plan("attendance.summary.by_supervisor.v1", rank=1, score=100),
            _build_plan("attendance.trend.daily.v1", rank=2, score=95),
        ]

    def plan_from_legacy(self, **kwargs):
        return dict(self.candidates[0])

    def plan_candidates_from_legacy(self, **kwargs):
        return [dict(item) for item in self.candidates]


class _FakeRouter:
    def __init__(self, *, fail_caps: set[str]):
        self.fail_caps = set(fail_caps)
        self.execute_calls: list[str] = []

    def route(self, **kwargs):
        planned = dict(kwargs.get("planned_capability") or {})
        capability_id = str(planned.get("capability_id") or "")
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
        planned = dict(kwargs.get("planned_capability") or {})
        capability_id = str(planned.get("capability_id") or "")
        self.execute_calls.append(capability_id)
        if capability_id in self.fail_caps:
            return {"ok": False, "error": f"failed:{capability_id}"}
        return {"ok": True, "response": _response("capability ok", capability_id)}


class _FakePolicyGuard:
    def evaluate(self, **kwargs):
        return PolicyDecision(
            action=PolicyAction.ALLOW,
            policy_id="policy.test.allow",
            reason="allow",
            metadata={},
        )


class _FakeBridge:
    def compare(self, **kwargs):
        planned = dict(kwargs.get("planned_capability") or {})
        capability_id = str(planned.get("capability_id") or "")
        return {
            "legacy_intent": "attendance_query",
            "legacy_domain": "attendance",
            "planned_capability_id": capability_id,
            "planned_capability_domain": capability_id.split(".", 1)[0] if "." in capability_id else "legacy",
            "diverged": False,
            "reason": "test",
        }


class _NoDelegationCoordinator:
    def plan_and_maybe_execute(self, **kwargs):
        return {
            "mode": "off",
            "should_delegate": False,
            "plan_reason": "",
            "selected_domains": [],
            "tasks": [],
            "executed": False,
            "response": None,
            "warnings": [],
        }


class _MemoryRuntimeStub:
    def load_context_for_chat(self, **kwargs):
        return {
            "flags": {"read_enabled": True, "write_enabled": True, "proposals_enabled": True},
            "decision": {"action": "read", "reason": "test"},
            "user_memory": [],
            "business_memory": [],
            "used": False,
        }

    def detect_candidates(self, **kwargs):
        return []

    def persist_candidates(self, **kwargs):
        return {"memory_candidates": [], "pending_proposals": [], "actions": []}


class LoopControllerIntegrationTests(SimpleTestCase):
    def _build_service(self, *, fail_caps: set[str]) -> tuple[ChatApplicationService, _FakeRouter]:
        fake_router = _FakeRouter(fail_caps=fail_caps)
        service = ChatApplicationService(
            planner=_FakePlanner(),
            router=fake_router,
            bridge=_FakeBridge(),
            policy_guard=_FakePolicyGuard(),
            memory_runtime=_MemoryRuntimeStub(),
            delegation_coordinator=_NoDelegationCoordinator(),
        )
        service._resolve_query_intelligence = lambda **_: {"mode": "off", "enabled": False}
        return service, fake_router

    def test_shadow_mode_does_not_alter_proactive_loop_flow(self):
        service, router = self._build_service(fail_caps={"attendance.summary.by_supervisor.v1"})
        legacy_runner = MagicMock(side_effect=AssertionError("legacy should not be called"))
        with patch.dict(
            os.environ,
            {
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_PROACTIVE_LOOP_ENABLED": "1",
                "IA_DEV_PROACTIVE_LOOP_MAX_ITERATIONS": "3",
                "IA_DEV_LOOP_CONTROLLER_ENABLED": "0",
                "IA_DEV_LOOP_CONTROLLER_SHADOW_ENABLED": "1",
            },
            clear=False,
        ):
            response = service.run(
                message="comparativo ausentismos",
                session_id="sess-lc-shadow",
                reset_memory=False,
                legacy_runner=legacy_runner,
                actor_user_key="user:test",
            )
        legacy_runner.assert_not_called()
        self.assertEqual(str(response.get("reply") or ""), "capability ok")
        self.assertEqual(router.execute_calls, ["attendance.summary.by_supervisor.v1", "attendance.trend.daily.v1"])

    def test_active_mode_does_not_break_proactive_loop(self):
        service, router = self._build_service(fail_caps={"attendance.summary.by_supervisor.v1"})
        legacy_runner = MagicMock(side_effect=AssertionError("legacy should not be called"))
        with patch.dict(
            os.environ,
            {
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_PROACTIVE_LOOP_ENABLED": "1",
                "IA_DEV_PROACTIVE_LOOP_MAX_ITERATIONS": "3",
                "IA_DEV_LOOP_CONTROLLER_ENABLED": "1",
                "IA_DEV_LOOP_CONTROLLER_SHADOW_ENABLED": "1",
            },
            clear=False,
        ):
            response = service.run(
                message="comparativo ausentismos",
                session_id="sess-lc-active",
                reset_memory=False,
                legacy_runner=legacy_runner,
                actor_user_key="user:test",
            )
        legacy_runner.assert_not_called()
        self.assertEqual(str(response.get("reply") or ""), "capability ok")
        self.assertEqual(router.execute_calls, ["attendance.summary.by_supervisor.v1", "attendance.trend.daily.v1"])

    def test_active_mode_preserves_legacy_fallback(self):
        service, router = self._build_service(
            fail_caps={"attendance.summary.by_supervisor.v1", "attendance.trend.daily.v1"}
        )
        legacy_runner = MagicMock(return_value=_response("legacy fallback", "attendance.summary.by_supervisor.v1"))
        with patch.dict(
            os.environ,
            {
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_PROACTIVE_LOOP_ENABLED": "1",
                "IA_DEV_PROACTIVE_LOOP_MAX_ITERATIONS": "3",
                "IA_DEV_LOOP_CONTROLLER_ENABLED": "1",
                "IA_DEV_LOOP_CONTROLLER_SHADOW_ENABLED": "1",
            },
            clear=False,
        ):
            response = service.run(
                message="comparativo ausentismos",
                session_id="sess-lc-legacy",
                reset_memory=False,
                legacy_runner=legacy_runner,
                actor_user_key="user:test",
            )
        self.assertEqual(router.execute_calls, ["attendance.summary.by_supervisor.v1", "attendance.trend.daily.v1"])
        legacy_runner.assert_called_once()
        self.assertEqual(str(response.get("reply") or ""), "legacy fallback")
