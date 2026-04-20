from __future__ import annotations

import os
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.orchestration.chat_application_service import (
    ChatApplicationService,
)
from apps.ia_dev.application.policies.policy_guard import (
    PolicyAction,
    PolicyDecision,
)
from apps.ia_dev.application.routing.capability_catalog import CapabilityCatalog


def _plan_for(service: ChatApplicationService, capability_id: str, *, reason: str) -> dict:
    definition = service.catalog.get(capability_id)
    domain = capability_id.split(".", 1)[0] if "." in capability_id else "general"
    return {
        "capability_id": capability_id,
        "capability_exists": bool(definition),
        "rollout_enabled": True,
        "handler_key": definition.handler_key if definition else "legacy.passthrough",
        "policy_tags": list(definition.policy_tags) if definition else [],
        "legacy_intents": list(definition.legacy_intents) if definition else [],
        "reason": reason,
        "source": {
            "intent": "general_question",
            "domain": domain,
            "output_mode": "summary",
            "needs_database": domain not in {"general", "legacy"},
        },
        "dictionary_hints": {},
        "candidate_rank": 1,
        "candidate_score": 95,
    }


def _legacy_response(reply: str) -> dict:
    return {
        "session_id": "sess-canonical-routing",
        "reply": reply,
        "orchestrator": {
            "intent": "general_question",
            "domain": "general",
            "selected_agent": "analista_agent",
            "classifier_source": "test",
            "needs_database": False,
            "output_mode": "summary",
            "used_tools": [],
        },
        "data": {"table": {"columns": [], "rows": [], "rowcount": 0}},
    }


class _ObservabilityStub:
    def __init__(self):
        self.events: list[dict] = []

    def record_event(self, *, event_type: str, source: str, meta: dict):
        self.events.append(
            {
                "event_type": str(event_type or ""),
                "source": str(source or ""),
                "meta": dict(meta or {}),
            }
        )


class CanonicalRoutingOverrideTests(SimpleTestCase):
    def setUp(self):
        self.service = ChatApplicationService()
        self.classification = {
            "intent": "general_question",
            "domain": "general",
            "selected_agent": "analista_agent",
            "needs_database": False,
            "output_mode": "summary",
            "used_tools": [],
            "dictionary_context": {},
        }

    def _run_override(
        self,
        *,
        message: str,
        canonical_resolution: dict,
        active: str,
        shadow: str,
    ) -> tuple[list[dict], RunContext]:
        run_context = RunContext.create(message=message, session_id="sess-canonical-routing")
        fallback_plan = _plan_for(self.service, "general.answer.v1", reason="fallback_general")
        candidate_plans = [_plan_for(self.service, "general.answer.v1", reason="runtime_general")]
        query_intelligence = {
            "mode": "active",
            "enabled": True,
            "canonical_resolution": canonical_resolution,
            "execution_plan": {},
            "precomputed_response": {},
        }
        with patch.dict(
            os.environ,
            {
                "IA_DEV_CANONICAL_ROUTING_ENABLED": active,
                "IA_DEV_CANONICAL_ROUTING_SHADOW_ENABLED": shadow,
            },
            clear=False,
        ):
            updated = self.service._apply_canonical_routing_overrides(
                message=message,
                candidate_plans=candidate_plans,
                fallback_plan=fallback_plan,
                query_intelligence=query_intelligence,
                classification=self.classification,
                run_context=run_context,
                observability=None,
            )
        return updated, run_context

    def test_empleados_vs_personal_converge_to_same_capability(self):
        canonical_empleados = {
            "canonical_query": "cantidad empleados activos",
            "domain_code": "empleados",
            "intent_code": "count",
            "capability_code": "",
            "confidence": 0.93,
            "conflicts": [],
        }
        canonical_personal = {
            "canonical_query": "cantidad empleados activos",
            "domain_code": "empleados",
            "intent_code": "count",
            "capability_code": "",
            "confidence": 0.92,
            "conflicts": [],
        }

        updated_empleados, _ = self._run_override(
            message="cantidad empleados activos",
            canonical_resolution=canonical_empleados,
            active="1",
            shadow="1",
        )
        updated_personal, _ = self._run_override(
            message="cantidad personal activo",
            canonical_resolution=canonical_personal,
            active="1",
            shadow="1",
        )

        capability_a = str(updated_empleados[0].get("capability_id") or "")
        capability_b = str(updated_personal[0].get("capability_id") or "")
        self.assertEqual(capability_a, "empleados.count.active.v1")
        self.assertEqual(capability_b, "empleados.count.active.v1")

    def test_strong_canonical_specific_domain_overrides_runtime_general_in_active_mode(self):
        canonical = {
            "canonical_query": "cantidad personal activo",
            "domain_code": "empleados",
            "intent_code": "count",
            "capability_code": "",
            "confidence": 0.91,
            "conflicts": [],
        }
        updated, run_context = self._run_override(
            message="cantidad personal activo",
            canonical_resolution=canonical,
            active="1",
            shadow="1",
        )

        self.assertEqual(str(updated[0].get("capability_id") or ""), "empleados.count.active.v1")
        routing_meta = dict(run_context.metadata.get("canonical_routing") or {})
        self.assertTrue(bool(routing_meta.get("influenced")))
        self.assertIn("runtime_general_vs_canonical_specific", list(routing_meta.get("differences") or []))

    def test_low_confidence_does_not_override_runtime(self):
        canonical = {
            "canonical_query": "cantidad personal activo",
            "domain_code": "empleados",
            "intent_code": "count",
            "capability_code": "",
            "confidence": 0.41,
            "conflicts": [],
        }
        updated, run_context = self._run_override(
            message="cantidad personal activo",
            canonical_resolution=canonical,
            active="1",
            shadow="1",
        )

        self.assertEqual(str(updated[0].get("capability_id") or ""), "general.answer.v1")
        routing_meta = dict(run_context.metadata.get("canonical_routing") or {})
        self.assertFalse(bool(routing_meta.get("influenced")))
        self.assertEqual(str(routing_meta.get("influence_reason") or ""), "canonical_low_confidence")

    def test_shadow_mode_logs_comparison_without_influencing_plan(self):
        canonical = {
            "canonical_query": "cantidad personal activo",
            "domain_code": "empleados",
            "intent_code": "count",
            "capability_code": "",
            "confidence": 0.95,
            "conflicts": [],
        }
        observability = _ObservabilityStub()
        run_context = RunContext.create(message="cantidad personal activo", session_id="sess-canonical-shadow")
        fallback_plan = _plan_for(self.service, "general.answer.v1", reason="fallback_general")
        candidate_plans = [_plan_for(self.service, "general.answer.v1", reason="runtime_general")]
        query_intelligence = {
            "mode": "active",
            "enabled": True,
            "canonical_resolution": canonical,
            "execution_plan": {},
            "precomputed_response": {},
        }

        with patch.dict(
            os.environ,
            {
                "IA_DEV_CANONICAL_ROUTING_ENABLED": "0",
                "IA_DEV_CANONICAL_ROUTING_SHADOW_ENABLED": "1",
            },
            clear=False,
        ):
            updated = self.service._apply_canonical_routing_overrides(
                message="cantidad personal activo",
                candidate_plans=candidate_plans,
                fallback_plan=fallback_plan,
                query_intelligence=query_intelligence,
                classification=self.classification,
                run_context=run_context,
                observability=observability,
            )

        self.assertEqual(str(updated[0].get("capability_id") or ""), "general.answer.v1")
        self.assertTrue(
            any(item.get("event_type") == "canonical_resolution_planner_router_comparison" for item in observability.events)
        )
        routing_meta = dict(run_context.metadata.get("canonical_routing") or {})
        self.assertFalse(bool(routing_meta.get("influenced")))
        self.assertEqual(str(routing_meta.get("influence_reason") or ""), "shadow_or_no_safe_runtime_correction_needed")


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


class _GeneralPlanner:
    def __init__(self, *, capability_id: str = "general.answer.v1"):
        self.capability_id = capability_id
        self.catalog = CapabilityCatalog()

    def plan_from_legacy(self, **kwargs):
        definition = self.catalog.get(self.capability_id)
        domain = self.capability_id.split(".", 1)[0] if "." in self.capability_id else "general"
        return {
            "capability_id": self.capability_id,
            "capability_exists": bool(definition),
            "rollout_enabled": True,
            "handler_key": definition.handler_key if definition else "legacy.passthrough",
            "policy_tags": list(definition.policy_tags) if definition else [],
            "legacy_intents": list(definition.legacy_intents) if definition else [],
            "reason": "planner_general_default",
            "source": {
                "intent": "general_question",
                "domain": domain,
                "output_mode": "summary",
                "needs_database": domain not in {"general", "legacy"},
            },
            "dictionary_hints": {},
            "candidate_rank": 1,
            "candidate_score": 95,
        }

    def plan_candidates_from_legacy(self, **kwargs):
        return [self.plan_from_legacy(**kwargs)]


class _DenyPolicyGuard:
    def evaluate(self, **kwargs):
        return PolicyDecision(
            action=PolicyAction.DENY,
            policy_id="policy.test.deny",
            reason="deny for policy continuity test",
            metadata={"runtime_action": "force_legacy_fallback"},
        )


class _AllowPolicyGuard:
    def evaluate(self, **kwargs):
        return PolicyDecision(
            action=PolicyAction.ALLOW,
            policy_id="policy.test.allow",
            reason="allow for legacy fallback continuity test",
            metadata={},
        )


class CanonicalRoutingPolicyAndFallbackTests(SimpleTestCase):
    def _build_service(self, *, policy_guard):
        service = ChatApplicationService(
            planner=_GeneralPlanner(capability_id="general.answer.v1"),
            policy_guard=policy_guard,
            memory_runtime=_MemoryRuntimeStub(),
            delegation_coordinator=_NoDelegationCoordinator(),
        )
        return service

    def test_policy_guard_still_controls_even_when_canonical_influences(self):
        service = self._build_service(policy_guard=_DenyPolicyGuard())
        service._resolve_query_intelligence = Mock(
            return_value={
                "mode": "active",
                "enabled": True,
                "canonical_resolution": {
                    "canonical_query": "cantidad empleados activos",
                    "domain_code": "empleados",
                    "intent_code": "count",
                    "capability_code": "empleados.count.active.v1",
                    "confidence": 0.97,
                    "conflicts": [],
                },
                "execution_plan": {},
                "classification_override": {},
                "precomputed_response": {},
            }
        )

        legacy_runner = MagicMock(return_value=_legacy_response("legacy from policy deny"))
        with patch.dict(
            os.environ,
            {
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_CANONICAL_ROUTING_ENABLED": "1",
                "IA_DEV_CANONICAL_ROUTING_SHADOW_ENABLED": "1",
            },
            clear=False,
        ):
            response = service.run(
                message="cantidad personal activo",
                session_id="sess-policy-canonical",
                reset_memory=False,
                legacy_runner=legacy_runner,
                actor_user_key="user:test",
            )

        legacy_runner.assert_called_once()
        self.assertEqual(str(response.get("reply") or ""), "legacy from policy deny")
        shadow = dict((response.get("orchestrator") or {}).get("capability_shadow") or {})
        self.assertEqual(str(((shadow.get("planned_capability") or {}).get("capability_id") or "")), "empleados.count.active.v1")
        self.assertEqual(str(((shadow.get("policy") or {}).get("action") or "")), "deny")

    def test_low_confidence_keeps_legacy_fallback_intact(self):
        service = self._build_service(policy_guard=_AllowPolicyGuard())
        service._resolve_query_intelligence = Mock(
            return_value={
                "mode": "active",
                "enabled": True,
                "canonical_resolution": {
                    "canonical_query": "cantidad personal activo",
                    "domain_code": "empleados",
                    "intent_code": "count",
                    "capability_code": "",
                    "confidence": 0.39,
                    "conflicts": [],
                },
                "execution_plan": {},
                "classification_override": {},
                "precomputed_response": {},
            }
        )

        legacy_runner = MagicMock(return_value=_legacy_response("legacy still intact"))
        with patch.dict(
            os.environ,
            {
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_CANONICAL_ROUTING_ENABLED": "1",
                "IA_DEV_CANONICAL_ROUTING_SHADOW_ENABLED": "1",
            },
            clear=False,
        ):
            response = service.run(
                message="cantidad personal activo",
                session_id="sess-fallback-canonical",
                reset_memory=False,
                legacy_runner=legacy_runner,
                actor_user_key="user:test",
            )

        legacy_runner.assert_called_once()
        self.assertEqual(str(response.get("reply") or ""), "legacy still intact")
        shadow = dict((response.get("orchestrator") or {}).get("capability_shadow") or {})
        self.assertEqual(str(((shadow.get("planned_capability") or {}).get("capability_id") or "")), "general.answer.v1")
