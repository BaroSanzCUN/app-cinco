from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from django.db import IntegrityError
from django.test import SimpleTestCase

from apps.ia_dev.application.memory.memory_write_service import MemoryWriteService


class MemoryWriteServiceIdempotencyTests(SimpleTestCase):
    def _build_service(self) -> MemoryWriteService:
        service = MemoryWriteService()
        service.repo = MagicMock()
        service.scope_classifier = SimpleNamespace(
            classify=lambda **_: SimpleNamespace(
                scope="business",
                sensitivity="medium",
                reason="classified as business",
                confidence=0.91,
            )
        )
        service.redactor = SimpleNamespace(redact_payload=lambda value: value)
        service.policy_guard = SimpleNamespace(
            evaluate_write=lambda **_: SimpleNamespace(
                action="require_approval",
                policy_id="memory.write.business.approval",
                reason="approval required",
                allow=False,
            )
        )
        service.workflow_state = SimpleNamespace(
            ensure_for_proposal=lambda **_: {"ok": True, "workflow": None},
            enrich_proposal=lambda proposal: proposal,
        )
        return service

    def test_create_proposal_handles_integrity_collision_as_idempotent(self):
        service = self._build_service()
        existing = {
            "proposal_id": "LMP-COLLIDE-01",
            "status": "pending",
            "idempotency_key": "idem-collision-01",
        }
        service.repo.get_learning_proposal_by_idempotency.side_effect = [None, existing]
        service.repo.create_learning_proposal.side_effect = IntegrityError("duplicate key")

        result = service.create_proposal(
            user_key="user:99",
            payload={
                "scope": "business",
                "candidate_key": "attendance.rule.recurrence",
                "candidate_value": {"threshold": 3},
                "reason": "regla reusable",
                "sensitivity": "medium",
                "idempotency_key": "idem-collision-01",
                "domain_code": "ATTENDANCE",
                "capability_id": "attendance.recurrence.detect.v1",
            },
            source_run_id="run-01",
        )

        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("idempotent"))
        self.assertEqual(result.get("proposal", {}).get("proposal_id"), "LMP-COLLIDE-01")

    def test_create_proposal_collision_without_existing_returns_safe_error(self):
        service = self._build_service()
        service.repo.get_learning_proposal_by_idempotency.side_effect = [None, None]
        service.repo.create_learning_proposal.side_effect = IntegrityError("duplicate key")

        result = service.create_proposal(
            user_key="user:99",
            payload={
                "scope": "business",
                "candidate_key": "attendance.rule.recurrence",
                "candidate_value": {"threshold": 2},
                "reason": "regla reusable",
                "sensitivity": "medium",
                "idempotency_key": "idem-collision-02",
            },
            source_run_id="run-02",
        )

        self.assertFalse(result.get("ok"))
        self.assertIn("colision concurrente", str(result.get("error")))
