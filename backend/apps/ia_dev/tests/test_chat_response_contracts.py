from __future__ import annotations

from django.test import SimpleTestCase

from apps.ia_dev.application.contracts.chat_contracts import (
    build_chat_response_snapshot,
    ensure_chat_response_contract,
)


class ChatResponseContractsTests(SimpleTestCase):
    def test_snapshot_includes_cause_generation_meta(self):
        snapshot = build_chat_response_snapshot()
        data = dict(snapshot.get("data") or {})
        self.assertIn("cause_generation_meta", data)
        self.assertIsInstance(data.get("cause_generation_meta"), dict)

    def test_ensure_contract_backfills_cause_generation_meta(self):
        response = ensure_chat_response_contract(
            {
                "session_id": "s1",
                "reply": "ok",
                "data": {"insights": [], "table": {"rows": [], "columns": []}},
            }
        )
        data = dict(response.get("data") or {})
        self.assertIn("cause_generation_meta", data)
        self.assertIsInstance(data.get("cause_generation_meta"), dict)
