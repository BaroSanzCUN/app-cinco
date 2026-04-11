from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.contracts.chat_contracts import ensure_chat_response_contract
from apps.ia_dev.application.policies.policy_guard import PolicyDecision


class LegacyResponseAssembler:
    def assemble(
        self,
        *,
        legacy_response: dict[str, Any],
        run_context: RunContext,
        planned_capability: dict[str, Any],
        route: dict[str, Any],
        policy_decision: PolicyDecision,
        divergence: dict[str, Any],
    ) -> dict[str, Any]:
        response = ensure_chat_response_contract(legacy_response)
        if not run_context.is_shadow_mode and not run_context.is_capability_mode_requested:
            return response

        orchestrator = response.get("orchestrator") or {}
        orchestrator["capability_shadow"] = {
            "run_id": run_context.run_id,
            "trace_id": run_context.trace_id,
            "routing_mode": run_context.routing_mode,
            "planned_capability": planned_capability,
            "route": route,
            "policy": {
                "action": policy_decision.action.value,
                "policy_id": policy_decision.policy_id,
                "reason": policy_decision.reason,
                "metadata": dict(policy_decision.metadata or {}),
            },
            "divergence": divergence,
        }
        response["orchestrator"] = orchestrator

        trace = response.get("trace") or []
        trace.append(
            self._trace_event(
                phase="capability_planner",
                status="ok",
                detail={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "planned_capability_id": planned_capability.get("capability_id"),
                    "reason": planned_capability.get("reason"),
                },
            )
        )
        trace.append(
            self._trace_event(
                phase="policy_guard",
                status="ok",
                detail={
                    "action": policy_decision.action.value,
                    "policy_id": policy_decision.policy_id,
                    "reason": policy_decision.reason,
                },
            )
        )
        trace.append(
            self._trace_event(
                phase="capability_router",
                status="ok",
                detail=route,
            )
        )
        trace.append(
            self._trace_event(
                phase="capability_divergence",
                status="warning" if divergence.get("diverged") else "ok",
                detail=divergence,
            )
        )
        response["trace"] = trace
        return response

    @staticmethod
    def _trace_event(*, phase: str, status: str, detail: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": phase,
            "status": status,
            "at": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
            "active_nodes": ["q", "gpt", "route"],
        }
