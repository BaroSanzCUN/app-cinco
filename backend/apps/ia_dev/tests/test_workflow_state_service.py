from __future__ import annotations

from contextlib import nullcontext
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ia_dev.application.workflow.workflow_state_service import WorkflowStateService


class _FakeWorkflowRepo:
    def __init__(self):
        self._states: dict[str, dict] = {}

    def get_workflow_state(self, workflow_key: str, *, for_update: bool = False):
        item = self._states.get(workflow_key)
        return dict(item) if item else None

    def upsert_workflow_state(
        self,
        *,
        workflow_type: str,
        workflow_key: str,
        status: str,
        state: dict,
        retry_count: int = 0,
        lock_version: int = 1,
        next_retry_at: int | None = None,
        last_error: str | None = None,
    ):
        existing = self._states.get(workflow_key)
        row = {
            "id": int((existing or {}).get("id") or (len(self._states) + 1)),
            "workflow_type": workflow_type,
            "workflow_key": workflow_key,
            "status": status,
            "state": dict(state or {}),
            "retry_count": int(retry_count),
            "lock_version": int(lock_version),
            "next_retry_at": next_retry_at,
            "last_error": last_error,
            "created_at": int((existing or {}).get("created_at") or 1),
            "updated_at": int((existing or {}).get("updated_at") or 1) + 1,
        }
        self._states[workflow_key] = row

    def list_workflow_states(self, *, workflow_type=None, status=None, limit: int = 100):
        rows = list(self._states.values())
        if workflow_type:
            rows = [item for item in rows if str(item.get("workflow_type") or "") == str(workflow_type)]
        if status:
            rows = [item for item in rows if str(item.get("status") or "") == str(status)]
        return [dict(item) for item in rows[:limit]]


class WorkflowStateServiceTests(SimpleTestCase):
    def setUp(self):
        self.repo = _FakeWorkflowRepo()
        self.service = WorkflowStateService(repo=self.repo)
        self.service.enabled = True
        self.service.enforce_transitions = True

    def test_proposal_transitions_pending_approved_applied(self):
        proposal = {
            "proposal_id": "LMP-WF-001",
            "scope": "business",
            "candidate_key": "attendance.rule",
            "status": "pending",
        }

        with patch("apps.ia_dev.application.workflow.workflow_state_service.transaction.atomic", return_value=nullcontext()):
            pending = self.service.ensure_for_proposal(
                proposal=proposal,
                status="pending",
                source="create",
                actor_user_key="user:1",
                actor_role="user",
            )
            approved = self.service.ensure_for_proposal(
                proposal={**proposal, "status": "approved"},
                status="approved",
                source="approve",
                actor_user_key="user:2",
                actor_role="lead",
            )
            applied = self.service.ensure_for_proposal(
                proposal={**proposal, "status": "applied"},
                status="applied",
                source="apply",
                actor_user_key="user:2",
                actor_role="lead",
            )

        self.assertTrue(pending.get("ok"))
        self.assertTrue(approved.get("ok"))
        self.assertTrue(applied.get("ok"))
        self.assertEqual(str((applied.get("workflow") or {}).get("status") or ""), "applied")

    def test_invalid_transition_is_blocked_when_enforced(self):
        proposal = {
            "proposal_id": "LMP-WF-002",
            "scope": "business",
            "candidate_key": "attendance.rule",
            "status": "applied",
        }
        with patch("apps.ia_dev.application.workflow.workflow_state_service.transaction.atomic", return_value=nullcontext()):
            self.service.ensure_for_proposal(
                proposal={**proposal, "status": "pending"},
                status="pending",
                source="create",
                actor_user_key="user:1",
                actor_role="user",
            )
            self.service.ensure_for_proposal(
                proposal=proposal,
                status="approved",
                source="approve",
                actor_user_key="user:2",
                actor_role="lead",
            )
            self.service.ensure_for_proposal(
                proposal=proposal,
                status="applied",
                source="apply",
                actor_user_key="user:2",
                actor_role="lead",
            )
            invalid = self.service.ensure_for_proposal(
                proposal={**proposal, "status": "pending"},
                status="pending",
                source="retry",
                actor_user_key="user:2",
                actor_role="lead",
            )

        self.assertFalse(invalid.get("ok"))
        self.assertEqual(str(invalid.get("error") or ""), "invalid_workflow_transition")

    def test_enrich_proposal_adds_workflow_fields(self):
        proposal = {
            "proposal_id": "LMP-WF-003",
            "scope": "user",
            "candidate_key": "attendance.output_mode",
            "status": "pending",
        }
        with patch("apps.ia_dev.application.workflow.workflow_state_service.transaction.atomic", return_value=nullcontext()):
            self.service.ensure_for_proposal(
                proposal=proposal,
                status="pending",
                source="create",
                actor_user_key="user:3",
                actor_role="user",
            )

        enriched = self.service.enrich_proposal(proposal)
        self.assertEqual(str(enriched.get("workflow_status") or ""), "pending")
        self.assertTrue(str(enriched.get("workflow_key") or "").startswith("memory_proposal:"))
