from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from apps.ia_dev.application.policies.policy_loader import PolicyLoader


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
    def __init__(self):
        self.loader = PolicyLoader()
        self._write_policy = self.loader.load("memory_write_policy.yaml")

    def evaluate_write(
        self,
        *,
        scope: str,
        sensitivity: str,
    ) -> MemoryPolicyDecision:
        s = str(scope or "").strip().lower()
        level = str(sensitivity or "medium").strip().lower()

        if s == "session":
            return MemoryPolicyDecision(
                action="allow",
                policy_id="memory.write.session.allow",
                reason="session memory is short-term and local",
            )
        if s == "user" and level in ("low", "medium"):
            return MemoryPolicyDecision(
                action="allow",
                policy_id="memory.write.user.allow",
                reason="user preference low/medium sensitivity",
            )
        if s == "workflow":
            return MemoryPolicyDecision(
                action="allow",
                policy_id="memory.write.workflow.allow",
                reason="workflow state is system managed",
            )
        if s in ("business", "general"):
            return MemoryPolicyDecision(
                action="require_approval",
                policy_id=f"memory.write.{s}.approval",
                reason="reusable/global memory requires governance approval",
            )
        if s == "user" and level == "high":
            return MemoryPolicyDecision(
                action="require_approval",
                policy_id="memory.write.user.high.approval",
                reason="high sensitivity user memory needs explicit approval",
            )
        return MemoryPolicyDecision(
            action="require_approval",
            policy_id="memory.write.default.approval",
            reason="default safety policy",
            metadata={"write_policy_loaded": bool(self._write_policy)},
        )
