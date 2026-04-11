from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from apps.ia_dev.application.context.run_context import RunContext


class PolicyAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


@dataclass(slots=True, frozen=True)
class PolicyDecision:
    action: PolicyAction
    policy_id: str
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.action == PolicyAction.ALLOW


class PolicyGuard:
    """
    PR1: base transversal no-bloqueante.
    Se deja listo el contrato de decision para evolucionar en PR2.
    """

    def evaluate(
        self,
        *,
        run_context: RunContext,
        planned_capability: dict[str, Any] | None,
    ) -> PolicyDecision:
        capability_id = str((planned_capability or {}).get("capability_id") or "")
        if not capability_id:
            return PolicyDecision(
                action=PolicyAction.ALLOW,
                policy_id="policy.base.allow.no_capability",
                reason="No capability selected. Keep legacy execution.",
                metadata={"routing_mode": run_context.routing_mode},
            )

        return PolicyDecision(
            action=PolicyAction.ALLOW,
            policy_id="policy.base.allow.default",
            reason="PR1 base policy keeps execution in legacy path.",
            metadata={
                "routing_mode": run_context.routing_mode,
                "capability_id": capability_id,
            },
        )
