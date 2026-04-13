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
        memory_effects: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = ensure_chat_response_contract(legacy_response)

        # Always expose memory loop outputs for incremental frontend adoption.
        effects = dict(memory_effects or {})
        existing_actions = list(response.get("actions") or [])
        injected_actions = list(effects.get("actions") or [])
        if injected_actions:
            existing_actions.extend(injected_actions)
        response["actions"] = existing_actions
        response["memory_candidates"] = list(effects.get("memory_candidates") or [])
        response["pending_proposals"] = list(effects.get("pending_proposals") or [])

        if not run_context.is_shadow_mode and not run_context.is_capability_mode_requested:
            return response

        orchestrator = response.get("orchestrator") or {}
        proactive_loop = dict(run_context.metadata.get("proactive_loop") or {})
        query_intelligence = dict(run_context.metadata.get("query_intelligence") or {})
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
            "memory": {
                "candidate_count": len(response.get("memory_candidates") or []),
                "pending_proposals_count": len(response.get("pending_proposals") or []),
            },
            "proactive_loop": proactive_loop,
            "query_intelligence": query_intelligence,
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
        if response.get("memory_candidates"):
            trace.append(
                self._trace_event(
                    phase="memory_feedback_loop",
                    status="ok",
                    detail={
                        "candidate_count": len(response.get("memory_candidates") or []),
                        "pending_count": len(response.get("pending_proposals") or []),
                    },
                )
            )
        if proactive_loop:
            trace.append(
                self._trace_event(
                    phase="proactive_loop",
                    status="ok" if not proactive_loop.get("used_legacy") else "warning",
                    detail={
                        "enabled": bool(proactive_loop.get("enabled")),
                        "iterations_ran": int(proactive_loop.get("iterations_ran") or 0),
                        "max_iterations": int(proactive_loop.get("max_iterations") or 0),
                        "selected_capability_id": proactive_loop.get("selected_capability_id"),
                        "used_legacy": bool(proactive_loop.get("used_legacy")),
                    },
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
