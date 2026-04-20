from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.orchestration.chat_application_service import (
    ChatApplicationService,
)
from apps.ia_dev.application.policies.policy_guard import (
    PolicyAction,
    PolicyDecision,
)
from apps.ia_dev.application.routing.capability_router import CapabilityRouter


def _response(reply: str, *, intent: str = "transport_query", used_tools: list[str] | None = None) -> dict:
    return {
        "session_id": "sess-pr8",
        "reply": reply,
        "orchestrator": {
            "intent": intent,
            "domain": "transport",
            "selected_agent": "transport_agent",
            "classifier_source": "test",
            "needs_database": True,
            "output_mode": "summary",
            "used_tools": used_tools or ["get_transport_departures_summary"],
        },
        "data": {
            "kpis": {"total_salidas": 9},
            "series": [9],
            "labels": ["2026-04-11"],
            "insights": [],
            "table": {
                "columns": ["fecha", "total_salidas"],
                "rows": [{"fecha": "2026-04-11", "total_salidas": 9}],
                "rowcount": 1,
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
    def __init__(self, planned_capability: dict):
        self._planned = dict(planned_capability)

    def plan_from_legacy(self, **kwargs):
        return dict(self._planned)


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
        return {
            "legacy_intent": "transport_query",
            "legacy_domain": "transport",
            "planned_capability_id": "transport.departures.summary.v1",
            "planned_capability_domain": "transport",
            "diverged": False,
            "reason": "test",
        }


class _FakeRouter:
    def __init__(self, *, execute_ok: bool):
        self.execute_ok = execute_ok
        self.execute_calls = 0

    def route(self, **kwargs):
        return {
            "routing_mode": "capability",
            "selected_capability_id": "transport.departures.summary.v1",
            "execute_capability": True,
            "use_legacy": False,
            "shadow_enabled": True,
            "reason": "test_execute_transport",
            "policy_action": "allow",
            "policy_allowed": True,
            "capability_exists": True,
            "rollout_enabled": True,
        }

    def execute(self, **kwargs):
        self.execute_calls += 1
        if self.execute_ok:
            return {"ok": True, "response": _response("capability transport ok")}
        return {"ok": False, "error": "handler_failed"}


class TransportCapabilityRouterTests(SimpleTestCase):
    def test_route_executes_transport_in_capability_mode_when_allowed(self):
        with patch.dict(os.environ, {"IA_DEV_ROUTING_MODE": "capability"}, clear=False):
            run_context = RunContext.create(message="cuantos vehiculos salieron hoy", session_id="s1")
            router = CapabilityRouter(
                attendance_handler=MagicMock(),
                transport_handler=MagicMock(),
            )
            decision = PolicyDecision(
                action=PolicyAction.ALLOW,
                policy_id="policy.allow",
                reason="allow",
                metadata={},
            )
            route = router.route(
                run_context=run_context,
                planned_capability={
                    "capability_id": "transport.departures.summary.v1",
                    "capability_exists": True,
                    "rollout_enabled": True,
                },
                policy_decision=decision,
            )

        self.assertTrue(route.get("execute_capability"))
        self.assertFalse(route.get("use_legacy"))

    def test_route_transport_falls_back_when_rollout_disabled(self):
        with patch.dict(os.environ, {"IA_DEV_ROUTING_MODE": "capability"}, clear=False):
            run_context = RunContext.create(message="cuantos vehiculos salieron hoy", session_id="s2")
            router = CapabilityRouter(
                attendance_handler=MagicMock(),
                transport_handler=MagicMock(),
            )
            decision = PolicyDecision(
                action=PolicyAction.ALLOW,
                policy_id="policy.allow",
                reason="allow",
                metadata={},
            )
            route = router.route(
                run_context=run_context,
                planned_capability={
                    "capability_id": "transport.departures.summary.v1",
                    "capability_exists": True,
                    "rollout_enabled": False,
                },
                policy_decision=decision,
            )

        self.assertFalse(route.get("execute_capability"))
        self.assertTrue(route.get("use_legacy"))
        self.assertEqual(route.get("reason"), "capability_rollout_disabled")


class ChatTransportCapabilityExecutionTests(SimpleTestCase):
    def _build_service(self, *, execute_ok: bool) -> tuple[ChatApplicationService, _FakeRouter]:
        planned = {
            "capability_id": "transport.departures.summary.v1",
            "capability_exists": True,
            "rollout_enabled": True,
            "handler_key": "transport.departures_summary",
            "policy_tags": ["contains_operational_data"],
            "legacy_intents": ["transport_query"],
            "reason": "test_plan",
            "source": {
                "intent": "transport_query",
                "domain": "transport",
                "output_mode": "summary",
                "needs_database": True,
            },
            "dictionary_hints": {},
        }
        fake_router = _FakeRouter(execute_ok=execute_ok)
        service = ChatApplicationService(
            planner=_FakePlanner(planned),
            router=fake_router,
            bridge=_FakeBridge(),
            policy_guard=_FakePolicyGuard(),
            memory_runtime=_FakeMemoryRuntime(),
        )
        return service, fake_router

    def test_chat_executes_transport_capability_without_legacy_when_handler_ok(self):
        with patch.dict(os.environ, {"IA_DEV_ROUTING_MODE": "capability"}, clear=False):
            service, fake_router = self._build_service(execute_ok=True)
            legacy_runner = MagicMock(side_effect=AssertionError("legacy should not be called"))
            response = service.run(
                message="cuantos vehiculos salieron hoy",
                session_id="sess-transport-a",
                reset_memory=False,
                legacy_runner=legacy_runner,
                actor_user_key="user:1",
            )

        self.assertEqual(response.get("reply"), "capability transport ok")
        self.assertEqual(fake_router.execute_calls, 1)
        legacy_runner.assert_not_called()

    def test_chat_fallbacks_to_legacy_when_transport_handler_fails(self):
        with patch.dict(os.environ, {"IA_DEV_ROUTING_MODE": "capability"}, clear=False):
            service, fake_router = self._build_service(execute_ok=False)
            legacy_runner = MagicMock(return_value=_response("legacy transport fallback"))
            response = service.run(
                message="cuantos vehiculos salieron hoy",
                session_id="sess-transport-b",
                reset_memory=False,
                legacy_runner=legacy_runner,
                actor_user_key="user:1",
            )

        self.assertEqual(fake_router.execute_calls, 1)
        legacy_runner.assert_called_once()
        self.assertEqual(response.get("reply"), "legacy transport fallback")
