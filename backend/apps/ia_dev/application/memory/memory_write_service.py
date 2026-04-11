from __future__ import annotations

import time
from django.db import IntegrityError, transaction

from apps.ia_dev.TOOLS.memory.memory_proposal_tool import build_memory_proposal
from apps.ia_dev.TOOLS.memory.memory_redaction_tool import MemoryRedactionTool
from apps.ia_dev.TOOLS.memory.memory_scope_classifier_tool import MemoryScopeClassifierTool
from apps.ia_dev.application.contracts.memory_contracts import (
    ensure_memory_proposal_payload,
    is_valid_memory_key,
    normalize_scope,
    normalize_sensitivity,
)
from apps.ia_dev.application.memory.repositories import MemoryRepository
from apps.ia_dev.application.policies.memory_policy_guard import MemoryPolicyGuard


class MemoryWriteService:
    def __init__(self):
        self.repo = MemoryRepository()
        self.scope_classifier = MemoryScopeClassifierTool()
        self.redactor = MemoryRedactionTool()
        self.policy_guard = MemoryPolicyGuard()
        self.db_alias = getattr(self.repo.store, "db_alias", "default")

    def write_user_preference(
        self,
        *,
        user_key: str,
        memory_key: str,
        memory_value,
        sensitivity: str = "low",
        source: str = "api",
    ) -> dict:
        clean_value = self.redactor.redact_payload(memory_value)
        record = self.repo.set_user_memory(
            user_key=user_key,
            memory_key=memory_key,
            memory_value=clean_value,
            sensitivity=normalize_sensitivity(sensitivity, default="low"),
            source=source,
            confidence=1.0,
        )
        self.repo.add_audit_event(
            event_type="memory_user_write",
            memory_scope="user",
            entity_key=f"{user_key}:{memory_key}",
            action="write",
            actor_type="user",
            actor_key=user_key,
            after=record,
            meta={"source": source},
        )
        return {
            "ok": True,
            "memory": record,
        }

    def create_proposal(
        self,
        *,
        user_key: str,
        payload: dict,
        source_run_id: str | None = None,
    ) -> dict:
        normalized = ensure_memory_proposal_payload(payload)
        candidate_key = str(normalized.get("candidate_key") or "").strip()
        if not candidate_key:
            return {"ok": False, "error": "candidate_key is required"}
        if len(candidate_key) > 120:
            return {"ok": False, "error": "candidate_key excede longitud maxima (120)"}
        if not is_valid_memory_key(candidate_key):
            return {"ok": False, "error": "candidate_key contiene caracteres no permitidos"}
        idempotency_key = str(normalized.get("idempotency_key") or "").strip() or None
        if idempotency_key:
            existing = self.repo.get_learning_proposal_by_idempotency(idempotency_key)
            if existing:
                return {"ok": True, "proposal": existing, "idempotent": True}

        classification = self.scope_classifier.classify(
            key=candidate_key,
            value_text=str(normalized.get("candidate_value")),
            requested_scope=normalized.get("scope"),
        )
        scope = normalize_scope(classification.scope)
        sensitivity = normalize_sensitivity(
            normalized.get("sensitivity") or classification.sensitivity
        )
        decision = self.policy_guard.evaluate_write(scope=scope, sensitivity=sensitivity)
        clean_value = self.redactor.redact_payload(normalized.get("candidate_value"))

        proposal = build_memory_proposal(
            scope=scope,
            proposer_user_key=user_key,
            candidate_key=candidate_key,
            candidate_value=clean_value,
            source_run_id=source_run_id,
            reason=normalized.get("reason") or classification.reason,
            sensitivity=sensitivity,
            idempotency_key=idempotency_key,
        )
        proposal["domain_code"] = normalized.get("domain_code")
        proposal["capability_id"] = normalized.get("capability_id")
        proposal["policy_action"] = decision.action
        proposal["policy_id"] = decision.policy_id
        try:
            created = self.repo.create_learning_proposal(proposal)
        except IntegrityError:
            if idempotency_key:
                existing = self.repo.get_learning_proposal_by_idempotency(idempotency_key)
                if existing:
                    return {
                        "ok": True,
                        "proposal": existing,
                        "idempotent": True,
                    }
            return {"ok": False, "error": "No fue posible crear propuesta por colision concurrente"}
        self.repo.add_audit_event(
            event_type="memory_proposal_created",
            memory_scope=scope,
            entity_key=str(created.get("proposal_id") or proposal["proposal_id"]),
            action="propose",
            actor_type="user",
            actor_key=user_key,
            after=created,
            meta={
                "policy_action": decision.action,
                "policy_id": decision.policy_id,
                "scope_classifier_reason": classification.reason,
                "scope_classifier_confidence": classification.confidence,
            },
        )

        auto_applied = False
        if decision.allow and scope == "user":
            apply_result = self.approve_proposal(
                proposal_id=str(created.get("proposal_id") or proposal["proposal_id"]),
                actor_user_key=user_key,
                actor_role="user",
                comment="auto_apply_user_low_risk",
            )
            auto_applied = bool(apply_result.get("ok"))
            created = apply_result.get("proposal") or created

        return {
            "ok": True,
            "proposal": created,
            "policy": {
                "action": decision.action,
                "policy_id": decision.policy_id,
                "reason": decision.reason,
            },
            "auto_applied": auto_applied,
        }

    def reject_proposal(
        self,
        *,
        proposal_id: str,
        actor_user_key: str,
        actor_role: str,
        comment: str = "",
    ) -> dict:
        pid = str(proposal_id or "").strip()
        if not pid:
            return {"ok": False, "error": "proposal_id is required"}
        with transaction.atomic(using=self.db_alias):
            proposal = self.repo.get_learning_proposal(pid, for_update=True)
            if not proposal:
                return {"ok": False, "error": "proposal_id not found"}
            status = str(proposal.get("status") or "")
            if status in ("rejected",):
                return {"ok": True, "proposal": proposal, "idempotent": True}
            if status in ("applied",):
                return {"ok": False, "error": "proposal already applied", "proposal": proposal}

            now = int(time.time())
            self.repo.update_learning_proposal(
                pid,
                {
                    "status": "rejected",
                    "updated_at": now,
                    "version": int(proposal.get("version") or 1) + 1,
                    "error": str(comment or "").strip() or "Rejected by reviewer",
                },
            )
            self.repo.add_learning_approval(
                {
                    "proposal_id": pid,
                    "action": "reject",
                    "actor_user_key": actor_user_key,
                    "actor_role": actor_role,
                    "comment": comment,
                    "created_at": now,
                }
            )
        final = self.repo.get_learning_proposal(pid) or {}
        self.repo.add_audit_event(
            event_type="memory_proposal_rejected",
            memory_scope=str(final.get("scope") or "user"),
            entity_key=pid,
            action="reject",
            actor_type="user",
            actor_key=actor_user_key,
            after=final,
            meta={"actor_role": actor_role, "comment": comment},
        )
        return {"ok": True, "proposal": final}

    def approve_proposal(
        self,
        *,
        proposal_id: str,
        actor_user_key: str,
        actor_role: str,
        comment: str = "",
    ) -> dict:
        pid = str(proposal_id or "").strip()
        if not pid:
            return {"ok": False, "error": "proposal_id is required"}

        with transaction.atomic(using=self.db_alias):
            proposal = self.repo.get_learning_proposal(pid, for_update=True)
            if not proposal:
                return {"ok": False, "error": "proposal_id not found"}

            status = str(proposal.get("status") or "")
            if status in ("applied", "approved"):
                return {"ok": True, "proposal": proposal, "idempotent": True}
            if status == "rejected":
                return {"ok": False, "error": "proposal rejected", "proposal": proposal}

            now = int(time.time())
            self.repo.update_learning_proposal(
                pid,
                {
                    "status": "approved",
                    "updated_at": now,
                    "version": int(proposal.get("version") or 1) + 1,
                },
            )
            self.repo.add_learning_approval(
                {
                    "proposal_id": pid,
                    "action": "approve",
                    "actor_user_key": actor_user_key,
                    "actor_role": actor_role,
                    "comment": comment,
                    "created_at": now,
                }
            )

        applied = self._apply_approved_proposal(
            proposal_id=pid,
            actor_user_key=actor_user_key,
            actor_role=actor_role,
        )
        return applied

    def _apply_approved_proposal(
        self,
        *,
        proposal_id: str,
        actor_user_key: str,
        actor_role: str,
    ) -> dict:
        pid = str(proposal_id or "").strip()
        with transaction.atomic(using=self.db_alias):
            proposal = self.repo.get_learning_proposal(pid, for_update=True)
            if not proposal:
                return {"ok": False, "error": "proposal_id not found"}
            if str(proposal.get("status")) == "applied":
                return {"ok": True, "proposal": proposal, "idempotent": True}
            if str(proposal.get("status")) != "approved":
                return {"ok": False, "error": "proposal must be approved first", "proposal": proposal}

            scope = normalize_scope(str(proposal.get("scope") or "user"))
            key = str(proposal.get("candidate_key") or "").strip()
            value = proposal.get("candidate_value")
            sensitivity = normalize_sensitivity(str(proposal.get("sensitivity") or "medium"))
            now = int(time.time())

            if scope == "user":
                self.repo.set_user_memory(
                    user_key=str(proposal.get("proposer_user_key") or "unknown"),
                    memory_key=key,
                    memory_value=value,
                    sensitivity=sensitivity,
                    source="proposal_approved",
                    confidence=1.0,
                )
            elif scope in ("business", "general"):
                try:
                    self.repo.set_business_memory(
                        domain_code=str(proposal.get("domain_code") or "GENERAL"),
                        capability_id=str(
                            proposal.get("capability_id") or ("general.learned.v1" if scope == "general" else "unknown")
                        ),
                        memory_key=key,
                        memory_value=value,
                        source_type="proposal_approved",
                        approved_by=actor_user_key,
                        approved_at=now,
                    )
                except IntegrityError:
                    # Carrera de insercion concurrente: se trata como idempotente.
                    pass
            else:
                return {"ok": False, "error": f"scope no soportado para apply: {scope}"}

            self.repo.update_learning_proposal(
                pid,
                {
                    "status": "applied",
                    "updated_at": now,
                    "version": int(proposal.get("version") or 1) + 1,
                    "error": None,
                },
            )

        final = self.repo.get_learning_proposal(pid) or {}
        self.repo.add_audit_event(
            event_type="memory_proposal_applied",
            memory_scope=str(final.get("scope") or "user"),
            entity_key=pid,
            action="apply",
            actor_type="user",
            actor_key=actor_user_key,
            after=final,
            meta={"actor_role": actor_role},
        )
        return {"ok": True, "proposal": final}
