from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class TerminationPolicyConfig:
    max_total_cycles: int = 3
    max_same_plan_retries: int = 1
    max_replans: int = 1
    max_llm_review_passes: int = 2
    approve_threshold: float = 0.85
    retry_same_plan_threshold: float = 0.60
    replan_threshold: float = 0.45


class TerminationPolicy:
    """
    Politica deterministica de control de ciclo/terminacion.
    """

    def __init__(self, *, config: TerminationPolicyConfig | None = None):
        self.config = config or TerminationPolicyConfig()

    def decide(
        self,
        *,
        cycle_index: int,
        strategy: str,
        satisfaction_score: float,
        gate_status: str,
        gate_result: dict[str, Any],
        execution: dict[str, Any],
        route: dict[str, Any],
        planned_capability: dict[str, Any],
        history: list[dict[str, Any]],
        same_plan_retries: int,
        replans_used: int,
        llm_review_passes: int,
    ) -> dict[str, Any]:
        score = float(satisfaction_score or 0.0)
        prior = [dict(item or {}) for item in list(history or []) if isinstance(item, dict)]
        capability_id = str((planned_capability or {}).get("capability_id") or "")
        issues = [
            str((row or {}).get("code") or "")
            for row in list((gate_result or {}).get("issues") or [])
            if isinstance(row, dict)
        ]
        error_signature = str(execution.get("error") or execution.get("satisfaction_reason") or "").strip().lower()

        no_improvement = self._is_no_improvement(prior=prior, current_score=score)
        same_error_repeated = self._is_same_error_repeated(prior=prior, error_signature=error_signature)
        evidence_unavailable = (
            not bool(gate_result.get("evidence_sufficient", True))
            or "low_evidence" in issues
        )
        policy_action = str((route or {}).get("policy_action") or "").strip().lower()
        policy_allowed = bool((route or {}).get("policy_allowed", True))
        policy_blocked = (not policy_allowed) or policy_action == "deny"
        high_risk_output = bool(gate_result.get("technical_leak_detected")) or ("technical_leak" in issues)
        budget_exhausted = bool(cycle_index >= int(self.config.max_total_cycles))

        requires_human_approval = policy_action == "require_approval"
        conflicting_sources_persist = self._conflicting_sources_persist(
            prior=prior,
            current_issues=issues,
        )
        sensitive_business_action = capability_id.startswith("knowledge.proposal.")
        third_failure = self._failure_count(prior=prior, gate_status=gate_status) >= 3

        stop_conditions = {
            "no_improvement": no_improvement,
            "same_error_repeated": same_error_repeated,
            "evidence_unavailable": evidence_unavailable,
            "policy_blocked": policy_blocked,
            "budget_exhausted": budget_exhausted,
            "high_risk_output": high_risk_output,
        }
        escalation_conditions = {
            "requires_human_approval": requires_human_approval,
            "conflicting_sources_persist": conflicting_sources_persist,
            "sensitive_business_action": sensitive_business_action,
            "third_failure": third_failure,
        }

        if str(gate_status or "") == "approved" and score >= float(self.config.approve_threshold):
            return {
                "decision": "approved",
                "stop_reason": "",
                "retry_reason": "",
                "next_action": "finalize_response",
                "approved": True,
                "should_continue": False,
                "stop_conditions": stop_conditions,
                "escalation_conditions": escalation_conditions,
                "error_signature": error_signature,
            }

        if high_risk_output:
            return self._stop_payload(
                stop_reason="high_risk_output",
                stop_conditions=stop_conditions,
                escalation_conditions=escalation_conditions,
                error_signature=error_signature,
            )
        if policy_blocked:
            return self._stop_payload(
                stop_reason="policy_blocked",
                stop_conditions=stop_conditions,
                escalation_conditions=escalation_conditions,
                error_signature=error_signature,
            )
        if same_error_repeated:
            return self._stop_payload(
                stop_reason="same_error_repeated",
                stop_conditions=stop_conditions,
                escalation_conditions=escalation_conditions,
                error_signature=error_signature,
            )
        if no_improvement:
            return self._stop_payload(
                stop_reason="no_improvement",
                stop_conditions=stop_conditions,
                escalation_conditions=escalation_conditions,
                error_signature=error_signature,
            )
        if evidence_unavailable:
            return {
                "decision": "ask_user",
                "stop_reason": "evidence_unavailable",
                "retry_reason": "missing_evidence_for_decision",
                "next_action": "ask_user_for_more_context",
                "approved": False,
                "should_continue": False,
                "stop_conditions": stop_conditions,
                "escalation_conditions": escalation_conditions,
                "error_signature": error_signature,
            }
        if requires_human_approval or conflicting_sources_persist or sensitive_business_action or third_failure:
            return {
                "decision": "escalate_human",
                "stop_reason": "escalation_condition_triggered",
                "retry_reason": "",
                "next_action": "escalate_to_human_reviewer",
                "approved": False,
                "should_continue": False,
                "stop_conditions": stop_conditions,
                "escalation_conditions": escalation_conditions,
                "error_signature": error_signature,
            }
        if budget_exhausted:
            return self._stop_payload(
                stop_reason="budget_exhausted",
                stop_conditions=stop_conditions,
                escalation_conditions=escalation_conditions,
                error_signature=error_signature,
            )

        if llm_review_passes >= int(self.config.max_llm_review_passes):
            return self._stop_payload(
                stop_reason="budget_exhausted",
                stop_conditions=stop_conditions,
                escalation_conditions=escalation_conditions,
                error_signature=error_signature,
            )

        if score >= float(self.config.retry_same_plan_threshold) and same_plan_retries < int(self.config.max_same_plan_retries):
            return {
                "decision": "retry_same_plan",
                "stop_reason": "",
                "retry_reason": "score_in_retry_window",
                "next_action": "retry_current_plan_once",
                "approved": False,
                "should_continue": True,
                "stop_conditions": stop_conditions,
                "escalation_conditions": escalation_conditions,
                "error_signature": error_signature,
            }

        if score >= float(self.config.replan_threshold) and replans_used < int(self.config.max_replans):
            return {
                "decision": "replan",
                "stop_reason": "",
                "retry_reason": "score_requires_replan",
                "next_action": "try_next_plan_candidate",
                "approved": False,
                "should_continue": True,
                "stop_conditions": stop_conditions,
                "escalation_conditions": escalation_conditions,
                "error_signature": error_signature,
            }

        if replans_used < int(self.config.max_replans) and cycle_index < int(self.config.max_total_cycles):
            return {
                "decision": "replan",
                "stop_reason": "",
                "retry_reason": "low_score_requires_replan",
                "next_action": "try_next_plan_candidate",
                "approved": False,
                "should_continue": True,
                "stop_conditions": stop_conditions,
                "escalation_conditions": escalation_conditions,
                "error_signature": error_signature,
            }

        return self._stop_payload(
            stop_reason="no_improvement",
            stop_conditions=stop_conditions,
            escalation_conditions=escalation_conditions,
            error_signature=error_signature,
        )

    @staticmethod
    def _stop_payload(
        *,
        stop_reason: str,
        stop_conditions: dict[str, bool],
        escalation_conditions: dict[str, bool],
        error_signature: str,
    ) -> dict[str, Any]:
        return {
            "decision": "stop",
            "stop_reason": str(stop_reason or "stop"),
            "retry_reason": "",
            "next_action": "stop_execution",
            "approved": False,
            "should_continue": False,
            "stop_conditions": dict(stop_conditions or {}),
            "escalation_conditions": dict(escalation_conditions or {}),
            "error_signature": str(error_signature or ""),
        }

    @staticmethod
    def _is_no_improvement(*, prior: list[dict[str, Any]], current_score: float) -> bool:
        scores = [
            float(row.get("satisfaction_score") or 0.0)
            for row in prior
            if isinstance(row, dict)
        ]
        if len(scores) < 2:
            return False
        prev = float(scores[-1])
        prev_prev = float(scores[-2])
        return current_score <= prev <= prev_prev

    @staticmethod
    def _is_same_error_repeated(*, prior: list[dict[str, Any]], error_signature: str) -> bool:
        current = str(error_signature or "").strip().lower()
        if not current:
            return False
        previous = str((prior[-1] if prior else {}).get("metadata", {}).get("error_signature") or "").strip().lower()
        return bool(previous and previous == current)

    @staticmethod
    def _conflicting_sources_persist(*, prior: list[dict[str, Any]], current_issues: list[str]) -> bool:
        conflict_codes = {"wrong_domain", "wrong_capability", "semantic_mismatch"}
        current = {item for item in list(current_issues or []) if item in conflict_codes}
        if not current:
            return False
        count = 1
        for row in reversed(prior):
            issues = {
                str(item or "")
                for item in list((row.get("metadata") or {}).get("issues") or [])
                if str(item or "") in conflict_codes
            }
            if not issues:
                break
            count += 1
            if count >= 2:
                return True
        return False

    @staticmethod
    def _failure_count(*, prior: list[dict[str, Any]], gate_status: str) -> int:
        failures = 0
        for row in list(prior or []):
            if str(row.get("gate_status") or "") != "approved":
                failures += 1
        if str(gate_status or "") != "approved":
            failures += 1
        return failures
