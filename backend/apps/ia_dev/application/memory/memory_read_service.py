from __future__ import annotations

from apps.ia_dev.application.memory.repositories import MemoryRepository


class MemoryReadService:
    def __init__(self):
        self.repo = MemoryRepository()

    def get_user_preferences(self, *, user_key: str, limit: int = 100) -> list[dict]:
        return self.repo.get_user_memory(user_key=user_key, limit=limit)

    def get_business_hints(
        self,
        *,
        domain_code: str | None = None,
        capability_id: str | None = None,
        memory_key_prefix: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        return self.repo.get_business_memory(
            domain_code=domain_code,
            capability_id=capability_id,
            memory_key_prefix=memory_key_prefix,
            limit=limit,
        )

    def get_audit_events(
        self,
        *,
        memory_scope: str | None = None,
        entity_key: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        return self.repo.list_audit_events(
            memory_scope=memory_scope,
            entity_key=entity_key,
            limit=limit,
        )
