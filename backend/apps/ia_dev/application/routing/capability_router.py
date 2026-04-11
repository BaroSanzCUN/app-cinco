from __future__ import annotations

from typing import Any

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.policies.policy_guard import PolicyDecision


class CapabilityRouter:
    """
    PR1 skeleton:
    - intent mode: legacy only
    - capability_shadow: legacy + traza de capability plan
    - capability: conserva legacy por compatibilidad (activacion real en PR2)
    """

    def route(
        self,
        *,
        run_context: RunContext,
        planned_capability: dict[str, Any],
        policy_decision: PolicyDecision,
    ) -> dict[str, Any]:
        capability_id = str(planned_capability.get("capability_id") or "legacy.passthrough.v1")
        routing_mode = run_context.routing_mode
        capability_exists = bool(planned_capability.get("capability_exists"))
        rollout_enabled = bool(planned_capability.get("rollout_enabled", True))

        if routing_mode == "intent":
            return {
                "routing_mode": routing_mode,
                "selected_capability_id": capability_id,
                "execute_capability": False,
                "use_legacy": True,
                "shadow_enabled": False,
                "reason": "intent_mode_keeps_legacy_path",
                "policy_action": policy_decision.action.value,
                "capability_exists": capability_exists,
                "rollout_enabled": rollout_enabled,
            }

        if routing_mode == "capability_shadow":
            return {
                "routing_mode": routing_mode,
                "selected_capability_id": capability_id,
                "execute_capability": False,
                "use_legacy": True,
                "shadow_enabled": True,
                "reason": "shadow_mode_computes_capability_but_executes_legacy",
                "policy_action": policy_decision.action.value,
                "capability_exists": capability_exists,
                "rollout_enabled": rollout_enabled,
            }

        # capability mode requested, but PR1 keeps safe fallback.
        return {
            "routing_mode": routing_mode,
            "selected_capability_id": capability_id,
            "execute_capability": False,
            "use_legacy": True,
            "shadow_enabled": True,
            "reason": "capability_mode_requested_pr1_forces_legacy_compat",
            "policy_action": policy_decision.action.value,
            "capability_exists": capability_exists,
            "rollout_enabled": rollout_enabled,
        }
