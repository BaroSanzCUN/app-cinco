from __future__ import annotations

from typing import Any

from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    LoopControllerDecision,
)
from apps.ia_dev.application.orchestration.termination_policy import (
    TerminationPolicy,
    TerminationPolicyConfig,
)


class LoopController:
    """
    Controlador explicito de ciclo de ejecucion/revision.
    Deterministic-first; sin reviewer LLM activo en esta fase.
    """

    def __init__(self, *, termination_policy: TerminationPolicy | None = None):
        self.termination_policy = termination_policy or TerminationPolicy(
            config=TerminationPolicyConfig()
        )

    def evaluate_cycle(
        self,
        *,
        cycle_index: int,
        strategy: str,
        planned_capability: dict[str, Any],
        route: dict[str, Any],
        execution: dict[str, Any],
        satisfaction: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
        same_plan_retries: int = 0,
        replans_used: int = 0,
        llm_review_passes: int = 0,
    ) -> LoopControllerDecision:
        sat = dict(satisfaction or {})
        gate = dict(sat.get("satisfaction_review_gate") or {})
        if gate:
            gate_status = "approved" if bool(gate.get("approved")) else "rejected"
            satisfaction_score = float(gate.get("satisfaction_score") or 0.0)
        else:
            gate_status = "approved" if bool(sat.get("satisfied", True)) else "rejected"
            satisfaction_score = 0.9 if bool(sat.get("satisfied", True)) else 0.35

        decision_payload = self.termination_policy.decide(
            cycle_index=int(cycle_index or 0),
            strategy=str(strategy or ""),
            satisfaction_score=satisfaction_score,
            gate_status=gate_status,
            gate_result=gate,
            execution=dict(execution or {}),
            route=dict(route or {}),
            planned_capability=dict(planned_capability or {}),
            history=[dict(item or {}) for item in list(history or []) if isinstance(item, dict)],
            same_plan_retries=int(same_plan_retries or 0),
            replans_used=int(replans_used or 0),
            llm_review_passes=int(llm_review_passes or 0),
        )
        decision = str(decision_payload.get("decision") or "stop")
        return LoopControllerDecision(
            cycle_index=int(cycle_index or 0),
            strategy=str(strategy or ""),
            satisfaction_score=float(satisfaction_score or 0.0),
            gate_status=gate_status,
            decision=decision,
            stop_reason=str(decision_payload.get("stop_reason") or ""),
            retry_reason=str(decision_payload.get("retry_reason") or ""),
            next_action=str(decision_payload.get("next_action") or "continue"),
            approved=bool(decision_payload.get("approved")),
            should_continue=bool(decision_payload.get("should_continue")),
            metadata={
                "issues": [
                    str((row or {}).get("code") or "")
                    for row in list(gate.get("issues") or [])
                    if isinstance(row, dict)
                ],
                "legacy_satisfied": bool(sat.get("satisfied", True)),
                "legacy_reason": str(sat.get("reason") or ""),
                "gate_next_action": str(gate.get("next_action") or ""),
                "gate_retry_reason": str(gate.get("retry_reason") or ""),
                "error_signature": str(decision_payload.get("error_signature") or ""),
                "stop_conditions": dict(decision_payload.get("stop_conditions") or {}),
                "escalation_conditions": dict(decision_payload.get("escalation_conditions") or {}),
                "same_plan_retries": int(same_plan_retries or 0),
                "replans_used": int(replans_used or 0),
                "llm_review_passes": int(llm_review_passes or 0),
            },
        )

