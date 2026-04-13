from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from apps.ia_dev.application.policies.policy_runtime import PolicyRuntime


@dataclass(slots=True, frozen=True)
class MemoryPolicyDecision:
    action: str
    policy_id: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def allow(self) -> bool:
        return self.action == "allow"

    @property
    def requires_approval(self) -> bool:
        return self.action == "require_approval"


class MemoryPolicyGuard:
    def __init__(self, *, runtime: PolicyRuntime | None = None):
        self.runtime = runtime or PolicyRuntime()
        self.runtime_enabled = str(os.getenv("IA_DEV_POLICY_RUNTIME_ENABLED", "1") or "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.failsafe_mode = str(os.getenv("IA_DEV_POLICY_FAILSAFE_MODE", "allow") or "allow").strip().lower()

    def evaluate_write(
        self,
        *,
        scope: str,
        sensitivity: str,
    ) -> MemoryPolicyDecision:
        s = str(scope or "").strip().lower()
        level = str(sensitivity or "medium").strip().lower()

        if not self.runtime_enabled:
            return self._fallback_decision(scope=s, sensitivity=level)

        fallback_action = "allow" if self.failsafe_mode == "allow" else "require_approval"
        try:
            runtime_decision = self.runtime.evaluate(
                policy_name="memory_write_policy.yaml",
                context={"scope": s, "sensitivity": level},
                fallback_action=fallback_action,
                fallback_policy_id="memory.write.runtime.fallback",
                fallback_reason="memory_write_policy_unavailable",
            )
        except Exception as exc:
            fallback = self._fallback_decision(scope=s, sensitivity=level)
            return MemoryPolicyDecision(
                action=fallback.action,
                policy_id="memory.write.runtime.exception",
                reason=f"Policy runtime exception: {exc}",
                metadata={
                    "scope": s,
                    "sensitivity": level,
                    "fallback_policy_id": fallback.policy_id,
                    "failsafe_mode": self.failsafe_mode,
                },
            )

        action = str(runtime_decision.action or "").strip().lower()
        if action in {"allow", "require_approval", "deny"}:
            return MemoryPolicyDecision(
                action=action,
                policy_id=str(runtime_decision.policy_id or "memory.write.runtime"),
                reason=str(runtime_decision.reason or "runtime decision"),
                metadata=dict(runtime_decision.metadata or {}),
            )

        # Unknown action: safe fallback
        fallback = self._fallback_decision(scope=s, sensitivity=level)
        return MemoryPolicyDecision(
            action=fallback.action,
            policy_id="memory.write.runtime.unknown_action",
            reason=(
                f"Unknown runtime action '{action}'. "
                f"Fallback to {fallback.action}."
            ),
            metadata={
                "scope": s,
                "sensitivity": level,
                "runtime_action": action,
                "fallback_policy_id": fallback.policy_id,
            },
        )

    @staticmethod
    def _fallback_decision(*, scope: str, sensitivity: str) -> MemoryPolicyDecision:
        if scope == "session":
            return MemoryPolicyDecision(
                action="allow",
                policy_id="memory.write.session.allow",
                reason="session memory is short-term and local",
            )
        if scope == "user" and sensitivity in ("low", "medium"):
            return MemoryPolicyDecision(
                action="allow",
                policy_id="memory.write.user.allow",
                reason="user preference low/medium sensitivity",
            )
        if scope == "workflow":
            return MemoryPolicyDecision(
                action="allow",
                policy_id="memory.write.workflow.allow",
                reason="workflow state is system managed",
            )
        if scope in ("business", "general"):
            return MemoryPolicyDecision(
                action="require_approval",
                policy_id=f"memory.write.{scope}.approval",
                reason="reusable/global memory requires governance approval",
            )
        if scope == "user" and sensitivity == "high":
            return MemoryPolicyDecision(
                action="require_approval",
                policy_id="memory.write.user.high.approval",
                reason="high sensitivity user memory needs explicit approval",
            )
        return MemoryPolicyDecision(
            action="require_approval",
            policy_id="memory.write.default.approval",
            reason="default safety policy",
        )
