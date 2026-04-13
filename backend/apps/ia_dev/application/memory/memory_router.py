from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.ia_dev.application.memory.memory_read_service import MemoryReadService
from apps.ia_dev.application.memory.memory_write_service import MemoryWriteService


@dataclass(frozen=True, slots=True)
class MemoryRoutingDecision:
    action: str
    reason: str
    metadata: dict[str, Any]


class MemoryRouter:
    def __init__(self):
        self.reader = MemoryReadService()
        self.writer = MemoryWriteService()

    def decide_for_chat(
        self,
        *,
        operation: str,
        scope: str | None = None,
        flags: dict[str, bool] | None = None,
    ) -> MemoryRoutingDecision:
        flags = dict(flags or {})
        op = str(operation or "").strip().lower()
        normalized_scope = str(scope or "").strip().lower()
        read_enabled = bool(flags.get("read_enabled", True))
        write_enabled = bool(flags.get("write_enabled", True))
        proposals_enabled = bool(flags.get("proposals_enabled", True))

        if op == "read":
            if read_enabled:
                return MemoryRoutingDecision(
                    action="read",
                    reason="memory_read_enabled",
                    metadata={"operation": op},
                )
            return MemoryRoutingDecision(
                action="ignore",
                reason="memory_read_disabled",
                metadata={"operation": op},
            )

        if op == "write":
            if write_enabled:
                return MemoryRoutingDecision(
                    action="write",
                    reason="memory_write_enabled",
                    metadata={"operation": op, "scope": normalized_scope},
                )
            return MemoryRoutingDecision(
                action="ignore",
                reason="memory_write_disabled",
                metadata={"operation": op, "scope": normalized_scope},
            )

        if op == "propose":
            if not proposals_enabled:
                return MemoryRoutingDecision(
                    action="ignore",
                    reason="memory_proposals_disabled",
                    metadata={"operation": op, "scope": normalized_scope},
                )
            if normalized_scope in {"business", "general"} and not write_enabled:
                return MemoryRoutingDecision(
                    action="ignore",
                    reason="memory_write_disabled_for_global_scope",
                    metadata={"operation": op, "scope": normalized_scope},
                )
            return MemoryRoutingDecision(
                action="propose",
                reason="memory_proposals_enabled",
                metadata={"operation": op, "scope": normalized_scope},
            )

        return MemoryRoutingDecision(
            action="ignore",
            reason="unsupported_operation",
            metadata={"operation": op, "scope": normalized_scope},
        )

    def propose_or_write(
        self,
        *,
        user_key: str,
        payload: dict,
        source_run_id: str | None = None,
    ) -> dict:
        scope = str(payload.get("scope") or "").strip().lower()
        if scope == "user" and bool(payload.get("direct_write", False)):
            return self.writer.write_user_preference(
                user_key=user_key,
                memory_key=str(payload.get("candidate_key") or ""),
                memory_value=payload.get("candidate_value"),
                sensitivity=str(payload.get("sensitivity") or "low"),
                source="direct_write",
            )
        return self.writer.create_proposal(
            user_key=user_key,
            payload=payload,
            source_run_id=source_run_id,
        )
