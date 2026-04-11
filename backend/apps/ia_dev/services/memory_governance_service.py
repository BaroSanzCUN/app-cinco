from __future__ import annotations

from apps.ia_dev.application.memory.memory_read_service import MemoryReadService
from apps.ia_dev.application.memory.memory_router import MemoryRouter
from apps.ia_dev.application.memory.memory_write_service import MemoryWriteService


class MemoryGovernanceService:
    def __init__(self):
        self.reader = MemoryReadService()
        self.writer = MemoryWriteService()
        self.router = MemoryRouter()

    def list_proposals(
        self,
        *,
        status: str | None = None,
        scope: str | None = None,
        proposer_user_key: str | None = None,
        limit: int = 30,
    ) -> list[dict]:
        return self.writer.repo.list_learning_proposals(
            status=status,
            scope=scope,
            proposer_user_key=proposer_user_key,
            limit=limit,
        )

    def create_proposal(
        self,
        *,
        user_key: str,
        payload: dict,
        source_run_id: str | None = None,
    ) -> dict:
        return self.router.propose_or_write(
            user_key=user_key,
            payload=payload,
            source_run_id=source_run_id,
        )

    def get_proposal(self, *, proposal_id: str) -> dict | None:
        return self.writer.repo.get_learning_proposal(proposal_id, for_update=False)

    def approve_proposal(
        self,
        *,
        proposal_id: str,
        actor_user_key: str,
        actor_role: str,
        comment: str = "",
    ) -> dict:
        return self.writer.approve_proposal(
            proposal_id=proposal_id,
            actor_user_key=actor_user_key,
            actor_role=actor_role,
            comment=comment,
        )

    def reject_proposal(
        self,
        *,
        proposal_id: str,
        actor_user_key: str,
        actor_role: str,
        comment: str = "",
    ) -> dict:
        return self.writer.reject_proposal(
            proposal_id=proposal_id,
            actor_user_key=actor_user_key,
            actor_role=actor_role,
            comment=comment,
        )

    def set_user_preference(
        self,
        *,
        user_key: str,
        memory_key: str,
        memory_value,
        sensitivity: str = "low",
        source: str = "api",
    ) -> dict:
        return self.writer.write_user_preference(
            user_key=user_key,
            memory_key=memory_key,
            memory_value=memory_value,
            sensitivity=sensitivity,
            source=source,
        )

    def get_user_preferences(self, *, user_key: str, limit: int = 100) -> list[dict]:
        return self.reader.get_user_preferences(user_key=user_key, limit=limit)

    def get_audit_events(
        self,
        *,
        memory_scope: str | None = None,
        entity_key: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        return self.reader.get_audit_events(memory_scope=memory_scope, entity_key=entity_key, limit=limit)
