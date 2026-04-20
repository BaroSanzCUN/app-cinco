from __future__ import annotations

import os
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    SatisfactionValidation,
)
from apps.ia_dev.application.orchestration.chat_application_service import (
    ChatApplicationService,
)
from apps.ia_dev.application.policies.policy_guard import (
    PolicyAction,
    PolicyDecision,
)
from apps.ia_dev.application.routing.capability_catalog import CapabilityCatalog


def _build_plan(capability_id: str, *, rank: int, score: int, reason: str) -> dict:
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
        "reason": reason,
        "source": {
            "intent": "general_question",
            "domain": domain,
            "output_mode": "summary",
            "needs_database": domain not in {"general", "legacy"},
        },
        "dictionary_hints": {},
        "query_constraints": {},
        "candidate_rank": rank,
        "candidate_score": score,
    }


class _FakePlanner:
    def __init__(self):
        self.candidates = [
            _build_plan("general.answer.v1", rank=1, score=100, reason="candidate_general"),
            _build_plan("empleados.count.active.v1", rank=2, score=95, reason="candidate_empleados"),
        ]

    def plan_from_legacy(self, **kwargs):
        return dict(self.candidates[0])

    def plan_candidates_from_legacy(self, **kwargs):
        return [dict(item) for item in self.candidates]


class _FakeRouter:
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
        if capability_id == "general.answer.v1":
            return {
                "ok": True,
                "response": {
                    "session_id": "sess-gate-int",
                    "reply": "respuesta general",
                    "orchestrator": {
                        "intent": "general_question",
                        "domain": "general",
                        "selected_agent": "analista_agent",
                        "classifier_source": "test",
                        "needs_database": False,
                        "output_mode": "summary",
                        "used_tools": [],
                    },
                    "data": {"kpis": {"total": 10}, "table": {"rows": [], "rowcount": 0}},
                },
            }
        return {
            "ok": True,
            "response": {
                "session_id": "sess-gate-int",
                "reply": "el total de empleados activos es 120",
                "orchestrator": {
                    "intent": "empleados_query",
                    "domain": "empleados",
                    "selected_agent": "empleados_agent",
                    "classifier_source": "test",
                    "needs_database": True,
                    "output_mode": "summary",
                    "used_tools": [],
                },
                "data": {"kpis": {"total_activos": 120}, "table": {"rows": [], "rowcount": 0}},
            },
        }


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
        planned = dict(kwargs.get("planned_capability") or {})
        capability_id = str(planned.get("capability_id") or "")
        return {
            "legacy_intent": "general_question",
            "legacy_domain": "general",
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


class SatisfactionReviewGateIntegrationTests(SimpleTestCase):
    def test_shadow_mode_does_not_alter_legacy_satisfaction_result(self):
        service = ChatApplicationService()
        service.result_satisfaction_validator = Mock()
        service.result_satisfaction_validator.validate.return_value = SatisfactionValidation(
            satisfied=True,
            reason="ok",
            checks={},
        )
        run_context = RunContext.create(message="cantidad personal activo", session_id="sess-shadow-gate")
        run_context.metadata["query_intelligence"] = {
            "canonical_resolution": {
                "domain_code": "empleados",
                "intent_code": "count",
                "capability_code": "empleados.count.active.v1",
                "confidence": 0.91,
            }
        }

        with patch.dict(
            os.environ,
            {
                "IA_DEV_SATISFACTION_REVIEW_GATE_ENABLED": "0",
                "IA_DEV_SATISFACTION_REVIEW_GATE_SHADOW_ENABLED": "1",
            },
            clear=False,
        ):
            result = service._evaluate_result_satisfaction(
                message="cantidad personal activo",
                planned_capability={"capability_id": "general.answer.v1"},
                execution={
                    "ok": True,
                    "response": {"reply": "respuesta general", "data": {"kpis": {"total": 10}, "table": {"rows": [], "rowcount": 0}}},
                    "used_legacy": False,
                    "fallback_reason": "",
                },
                resolved_query=None,
                execution_plan=None,
                run_context=run_context,
                observability=None,
                loop_iteration=1,
                route={"reason": "test"},
            )

        self.assertTrue(bool(result.get("satisfied")))
        self.assertEqual(str(result.get("reason") or ""), "ok")
        self.assertIn("satisfaction_review_gate", result)
        comparison = dict(result.get("satisfaction_review_gate_comparison") or {})
        self.assertTrue(bool(comparison.get("differences_count")))

    def test_active_mode_keeps_proactive_loop_working(self):
        service = ChatApplicationService(
            planner=_FakePlanner(),
            router=_FakeRouter(),
            bridge=_FakeBridge(),
            policy_guard=_FakePolicyGuard(),
            memory_runtime=_MemoryRuntimeStub(),
            delegation_coordinator=_NoDelegationCoordinator(),
        )
        service.result_satisfaction_validator = Mock()
        service.result_satisfaction_validator.validate.return_value = SatisfactionValidation(
            satisfied=True,
            reason="ok",
            checks={},
        )

        def _qi_stub(*, message: str, base_classification: dict, session_context=None, run_context: RunContext, observability):
            payload = {
                "mode": "off",
                "enabled": False,
                "canonical_resolution": {
                    "domain_code": "empleados",
                    "intent_code": "count",
                    "capability_code": "empleados.count.active.v1",
                    "confidence": 0.96,
                    "conflicts": [],
                },
                "resolved_query": {
                    "intent": {
                        "raw_query": message,
                        "domain_code": "empleados",
                        "operation": "count",
                        "template_id": "count_entities_by_status",
                        "filters": {"estado": "ACTIVO"},
                        "period": {},
                        "group_by": [],
                        "metrics": ["count"],
                        "confidence": 0.9,
                        "source": "rules",
                        "warnings": [],
                    },
                    "semantic_context": {},
                    "normalized_filters": {"estado": "ACTIVO"},
                    "normalized_period": {},
                    "mapped_columns": {},
                    "warnings": [],
                },
                "execution_plan": {
                    "strategy": "capability",
                    "reason": "test",
                    "domain_code": "empleados",
                    "capability_id": "empleados.count.active.v1",
                    "constraints": {},
                    "policy": {},
                    "metadata": {},
                },
                "classification_override": {},
                "precomputed_response": {},
            }
            run_context.metadata["query_intelligence"] = dict(payload)
            run_context.metadata["canonical_resolution"] = dict(payload.get("canonical_resolution") or {})
            return payload

        service._resolve_query_intelligence = _qi_stub

        legacy_runner = MagicMock(return_value={"reply": "legacy should not be used"})
        with patch.dict(
            os.environ,
            {
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_PROACTIVE_LOOP_ENABLED": "1",
                "IA_DEV_PROACTIVE_LOOP_MAX_ITERATIONS": "3",
                "IA_DEV_CANONICAL_ROUTING_ENABLED": "0",
                "IA_DEV_CANONICAL_ROUTING_SHADOW_ENABLED": "0",
                "IA_DEV_SATISFACTION_REVIEW_GATE_ENABLED": "1",
                "IA_DEV_SATISFACTION_REVIEW_GATE_SHADOW_ENABLED": "1",
            },
            clear=False,
        ):
            response = service.run(
                message="cantidad personal activo",
                session_id="sess-active-gate",
                reset_memory=False,
                legacy_runner=legacy_runner,
                actor_user_key="user:test",
            )

        legacy_runner.assert_not_called()
        self.assertEqual(str(response.get("reply") or ""), "el total de empleados activos es 120")
        loop_meta = dict(((response.get("orchestrator") or {}).get("capability_shadow") or {}).get("proactive_loop") or {})
        self.assertTrue(bool(loop_meta.get("enabled")))
        self.assertEqual(int(loop_meta.get("iterations_ran") or 0), 2)
        qi_meta = dict(((response.get("orchestrator") or {}).get("capability_shadow") or {}).get("query_intelligence") or {})
        gate_audit = dict(qi_meta.get("satisfaction_review_gate_audit") or {})
        self.assertIn("approved", gate_audit)
        self.assertIn("satisfaction_score", gate_audit)
        self.assertIn("next_action", gate_audit)
        self.assertIn("issues_count", gate_audit)
        self.assertIn("retry_reason", gate_audit)
