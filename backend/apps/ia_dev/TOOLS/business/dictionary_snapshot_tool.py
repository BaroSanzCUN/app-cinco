from __future__ import annotations

from typing import Any

from apps.ia_dev.services.dictionary_tool_service import DictionaryToolService


class DictionarySnapshotTool:
    def __init__(self):
        self._service = DictionaryToolService()

    def get_snapshot(self) -> dict[str, Any]:
        return self._service.get_dictionary_snapshot()

    def get_domain_context(self, domain: str, *, limit: int = 8) -> dict[str, Any]:
        return self._service.get_domain_context(domain=domain, limit=limit)
