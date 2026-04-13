from __future__ import annotations

from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.policies.memory_policy_guard import MemoryPolicyGuard
from apps.ia_dev.application.policies.policy_guard import PolicyAction, PolicyGuard
from apps.ia_dev.application.policies.policy_runtime import PolicyRuntime


class PolicyRuntimeTests(SimpleTestCase):
    def test_runtime_fallback_when_policy_not_found(self):
        runtime = PolicyRuntime()
        decision = runtime.evaluate(
            policy_name="missing_policy.yaml",
            context={"routing_mode": "capability"},
            fallback_action="deny",
            fallback_policy_id="fallback.test",
            fallback_reason="missing",
        )
        self.assertEqual(decision.action, "deny")
        self.assertEqual(decision.policy_id, "fallback.test")
        self.assertTrue(decision.metadata.get("fallback"))

    def test_policy_guard_uses_yaml_runtime_decision(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_POLICY_RUNTIME_ENABLED": "1",
                "IA_DEV_POLICY_FAILSAFE_MODE": "allow",
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_POLICY_CAPABILITY_EXECUTION_ENABLED": "0",
            },
            clear=False,
        ):
            run_context = RunContext.create(message="dame tabla ausentismo", session_id="p-1")
            guard = PolicyGuard()
            decision = guard.evaluate(
                run_context=run_context,
                planned_capability={
                    "capability_id": "attendance.unjustified.table.v1",
                    "policy_tags": ["contains_personal_data"],
                    "source": {"needs_database": True},
                },
            )

        self.assertEqual(decision.action, PolicyAction.DENY)
        self.assertEqual(decision.policy_id, "capability.execution.disabled")
        self.assertEqual(str(decision.metadata.get("runtime_action") or ""), "force_legacy_fallback")

    def test_memory_policy_guard_reads_yaml_rules(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_POLICY_RUNTIME_ENABLED": "1",
                "IA_DEV_POLICY_FAILSAFE_MODE": "allow",
            },
            clear=False,
        ):
            guard = MemoryPolicyGuard()
            decision_user = guard.evaluate_write(scope="user", sensitivity="low")
            decision_business = guard.evaluate_write(scope="business", sensitivity="medium")

        self.assertEqual(decision_user.action, "allow")
        self.assertEqual(decision_business.action, "require_approval")

    def test_policy_guard_denies_transport_when_rollout_disabled(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_POLICY_RUNTIME_ENABLED": "1",
                "IA_DEV_POLICY_FAILSAFE_MODE": "allow",
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_POLICY_CAPABILITY_EXECUTION_ENABLED": "1",
                "IA_DEV_CAP_TRANSPORT_ENABLED": "0",
            },
            clear=False,
        ):
            run_context = RunContext.create(message="cuantos vehiculos salieron hoy", session_id="p-8")
            guard = PolicyGuard()
            decision = guard.evaluate(
                run_context=run_context,
                planned_capability={
                    "capability_id": "transport.departures.summary.v1",
                    "policy_tags": ["contains_operational_data"],
                    "source": {"needs_database": True},
                },
            )

        self.assertEqual(decision.action, PolicyAction.DENY)
        self.assertEqual(decision.policy_id, "transport.capability.disabled")
        self.assertEqual(str(decision.metadata.get("runtime_action") or ""), "disable_capability")
