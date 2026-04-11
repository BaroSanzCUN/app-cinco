from __future__ import annotations

import os
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


def _flag_enabled(name: str, default: str = "1") -> bool:
    value = os.getenv(name, default)
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


class PolicyGuard:
    """
    Guard transversal incremental para capability-first.
    No rompe legacy: en intent/shadow permite y deja trazabilidad.
    """

    def evaluate(
        self,
        *,
        run_context: RunContext,
        planned_capability: dict[str, Any] | None,
    ) -> PolicyDecision:
        planned = dict(planned_capability or {})
        capability_id = str(planned.get("capability_id") or "").strip()
        routing_mode = run_context.routing_mode

        if not capability_id:
            return PolicyDecision(
                action=PolicyAction.ALLOW,
                policy_id="policy.base.allow.no_capability",
                reason="No capability selected. Keep legacy execution.",
                metadata={"routing_mode": routing_mode},
            )

        if routing_mode in {"intent", "capability_shadow"}:
            return PolicyDecision(
                action=PolicyAction.ALLOW,
                policy_id="policy.base.allow.non_blocking_mode",
                reason="Intent/shadow mode preserves legacy compatibility.",
                metadata={
                    "routing_mode": routing_mode,
                    "capability_id": capability_id,
                },
            )

        if not _flag_enabled("IA_DEV_POLICY_CAPABILITY_EXECUTION_ENABLED", "1"):
            return PolicyDecision(
                action=PolicyAction.DENY,
                policy_id="policy.capability.execution.disabled",
                reason="Capability execution is disabled by policy flag.",
                metadata={
                    "routing_mode": routing_mode,
                    "capability_id": capability_id,
                },
            )

        if capability_id.startswith("attendance."):
            return self._evaluate_attendance_policy(
                run_context=run_context,
                planned_capability=planned,
                capability_id=capability_id,
            )

        return PolicyDecision(
            action=PolicyAction.ALLOW,
            policy_id="policy.base.allow.default",
            reason="Capability allowed by default policy.",
            metadata={
                "routing_mode": routing_mode,
                "capability_id": capability_id,
            },
        )

    def _evaluate_attendance_policy(
        self,
        *,
        run_context: RunContext,
        planned_capability: dict[str, Any],
        capability_id: str,
    ) -> PolicyDecision:
        policy_tags = set(planned_capability.get("policy_tags") or [])
        source = dict(planned_capability.get("source") or {})
        needs_database = bool(source.get("needs_database", True))
        memory_preloaded = dict((run_context.metadata.get("memory_context") or {}).get("preloaded") or {})
        uses_memory = (
            int(memory_preloaded.get("user_memory_count") or 0) > 0
            or int(memory_preloaded.get("business_memory_count") or 0) > 0
        )

        if not _flag_enabled("IA_DEV_CAP_ATTENDANCE_ENABLED", "0"):
            return PolicyDecision(
                action=PolicyAction.DENY,
                policy_id="policy.attendance.capability.disabled",
                reason="Attendance capability-first is disabled.",
                metadata={"capability_id": capability_id},
            )

        if not needs_database:
            return PolicyDecision(
                action=PolicyAction.DENY,
                policy_id="policy.attendance.requires_database",
                reason="Attendance capability requires database access.",
                metadata={"capability_id": capability_id},
            )

        requires_personal_join = capability_id in {
            "attendance.unjustified.table_with_personal.v1",
            "attendance.recurrence.grouped.v1",
            "attendance.recurrence.itemized.v1",
        }
        if requires_personal_join and not _flag_enabled(
            "IA_DEV_POLICY_ATTENDANCE_PERSONAL_JOIN_ENABLED", "1"
        ):
            return PolicyDecision(
                action=PolicyAction.DENY,
                policy_id="policy.attendance.personal_join.disabled",
                reason="Join con personal esta restringido por politica.",
                metadata={"capability_id": capability_id, "requires_personal_join": True},
            )

        if uses_memory and not _flag_enabled("IA_DEV_POLICY_MEMORY_HINTS_ENABLED", "1"):
            return PolicyDecision(
                action=PolicyAction.DENY,
                policy_id="policy.attendance.memory_hints.disabled",
                reason="Uso de memory hints deshabilitado por politica.",
                metadata={"capability_id": capability_id, "uses_memory": uses_memory},
            )

        return PolicyDecision(
            action=PolicyAction.ALLOW,
            policy_id="policy.attendance.allow",
            reason="Attendance capability allowed by policy.",
            metadata={
                "capability_id": capability_id,
                "requires_personal_join": requires_personal_join,
                "contains_personal_data": "contains_personal_data" in policy_tags,
                "uses_memory_hints": uses_memory,
            },
        )
