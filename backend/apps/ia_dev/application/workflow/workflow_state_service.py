from __future__ import annotations

import os
import time
from typing import Any

from django.db import transaction

from apps.ia_dev.application.memory.repositories import MemoryRepository


class WorkflowStateService:
    WORKFLOW_TYPE_MEMORY_PROPOSAL = "memory_proposal"
    TERMINAL_STATES = {"rejected", "applied", "failed", "expired"}
    VALID_TRANSITIONS = {
        "pending": {"approved", "rejected", "expired", "failed"},
        "approved": {"applied", "rejected", "failed", "expired"},
        "failed": {"pending", "expired"},
        "rejected": set(),
        "applied": set(),
        "expired": set(),
    }

    def __init__(self, *, repo: MemoryRepository | None = None):
        self.repo = repo or MemoryRepository()
        self.db_alias = getattr(self.repo.store, "db_alias", "default")
        self.enabled = str(os.getenv("IA_DEV_WORKFLOW_STATE_ENABLED", "1") or "1").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.enforce_transitions = str(
            os.getenv("IA_DEV_WORKFLOW_ENFORCE_TRANSITIONS", "1") or "1"
        ).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def workflow_key_for_proposal(proposal_id: str) -> str:
        return f"memory_proposal:{str(proposal_id or '').strip()}"

    def ensure_for_proposal(
        self,
        *,
        proposal: dict[str, Any],
        status: str,
        source: str,
        actor_user_key: str | None = None,
        actor_role: str | None = None,
        comment: str | None = None,
        error: str | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": True, "workflow": None, "disabled": True}
        proposal_id = str(proposal.get("proposal_id") or "").strip()
        if not proposal_id:
            return {"ok": False, "error": "proposal_id_missing"}
        workflow_key = self.workflow_key_for_proposal(proposal_id)

        with transaction.atomic(using=self.db_alias):
            existing = self.repo.get_workflow_state(workflow_key, for_update=True)
            current_status = str((existing or {}).get("status") or "").strip().lower() if existing else ""
            target_status = str(status or "pending").strip().lower() or "pending"

            if existing and current_status == target_status:
                # Actualiza metadata de estado aun si la transicion es idempotente.
                merged_state = self._merge_state(
                    base_state=dict(existing.get("state") or {}),
                    proposal=proposal,
                    target_status=target_status,
                    source=source,
                    actor_user_key=actor_user_key,
                    actor_role=actor_role,
                    comment=comment,
                    error=error,
                )
                self.repo.upsert_workflow_state(
                    workflow_type=self.WORKFLOW_TYPE_MEMORY_PROPOSAL,
                    workflow_key=workflow_key,
                    status=target_status,
                    state=merged_state,
                    retry_count=int(existing.get("retry_count") or 0),
                    lock_version=int(existing.get("lock_version") or 1) + 1,
                    next_retry_at=existing.get("next_retry_at"),
                    last_error=error if error is not None else existing.get("last_error"),
                )
                refreshed = self.repo.get_workflow_state(workflow_key) or {}
                return {"ok": True, "workflow": refreshed, "idempotent": True}

            if self.enforce_transitions and existing and current_status:
                allowed = set(self.VALID_TRANSITIONS.get(current_status, set()))
                if target_status not in allowed:
                    return {
                        "ok": False,
                        "error": "invalid_workflow_transition",
                        "workflow": existing,
                        "from_status": current_status,
                        "to_status": target_status,
                    }

            retry_count = int((existing or {}).get("retry_count") or 0)
            if target_status == "failed":
                retry_count += 1

            merged_state = self._merge_state(
                base_state=dict((existing or {}).get("state") or {}),
                proposal=proposal,
                target_status=target_status,
                source=source,
                actor_user_key=actor_user_key,
                actor_role=actor_role,
                comment=comment,
                error=error,
            )
            self.repo.upsert_workflow_state(
                workflow_type=self.WORKFLOW_TYPE_MEMORY_PROPOSAL,
                workflow_key=workflow_key,
                status=target_status,
                state=merged_state,
                retry_count=retry_count,
                lock_version=int((existing or {}).get("lock_version") or 1) + (1 if existing else 0),
                next_retry_at=None,
                last_error=error,
            )

        refreshed = self.repo.get_workflow_state(workflow_key) or {}
        return {"ok": True, "workflow": refreshed, "idempotent": False}

    def get_for_proposal(self, proposal_id: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        pid = str(proposal_id or "").strip()
        if not pid:
            return None
        return self.repo.get_workflow_state(self.workflow_key_for_proposal(pid))

    def enrich_proposal(self, proposal: dict[str, Any] | None) -> dict[str, Any]:
        payload = dict(proposal or {})
        proposal_id = str(payload.get("proposal_id") or "").strip()
        if not proposal_id:
            return payload
        workflow = self.get_for_proposal(proposal_id)
        if workflow:
            payload["workflow"] = workflow
            payload["workflow_status"] = str(workflow.get("status") or "")
            payload["workflow_key"] = str(workflow.get("workflow_key") or "")
        return payload

    def list_proposal_workflows(
        self,
        *,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        return self.repo.list_workflow_states(
            workflow_type=self.WORKFLOW_TYPE_MEMORY_PROPOSAL,
            status=status,
            limit=limit,
        )

    @staticmethod
    def _merge_state(
        *,
        base_state: dict[str, Any],
        proposal: dict[str, Any],
        target_status: str,
        source: str,
        actor_user_key: str | None,
        actor_role: str | None,
        comment: str | None,
        error: str | None,
    ) -> dict[str, Any]:
        state = dict(base_state or {})
        state.update(
            {
                "proposal_id": str(proposal.get("proposal_id") or ""),
                "scope": str(proposal.get("scope") or "").strip().lower(),
                "status": target_status,
                "candidate_key": str(proposal.get("candidate_key") or ""),
                "capability_id": str(proposal.get("capability_id") or "") if proposal.get("capability_id") else None,
                "domain_code": str(proposal.get("domain_code") or "") if proposal.get("domain_code") else None,
                "policy_action": str(proposal.get("policy_action") or "") if proposal.get("policy_action") else None,
                "proposer_user_key": str(proposal.get("proposer_user_key") or "") if proposal.get("proposer_user_key") else None,
            }
        )

        now = int(time.time())
        transition = {
            "at": now,
            "to": target_status,
            "source": source,
            "actor_user_key": str(actor_user_key or "") or None,
            "actor_role": str(actor_role or "") or None,
            "comment": str(comment or "") or None,
            "error": str(error or "") or None,
        }
        history = list(state.get("transition_history") or [])
        history.append(transition)
        state["transition_history"] = history[-20:]
        state["last_transition"] = transition
        state["updated_at"] = now
        if "created_at" not in state:
            state["created_at"] = now
        return state
