from __future__ import annotations

import time
import uuid
from typing import Any


def build_memory_proposal(
    *,
    scope: str,
    proposer_user_key: str,
    candidate_key: str,
    candidate_value: Any,
    source_run_id: str | None = None,
    reason: str = "",
    sensitivity: str = "medium",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    now = int(time.time())
    proposal_id = f"MPRO-{uuid.uuid4().hex[:10].upper()}"
    return {
        "proposal_id": proposal_id,
        "scope": str(scope or "").strip().lower(),
        "status": "pending",
        "proposer_user_key": str(proposer_user_key or "").strip() or "unknown",
        "source_run_id": str(source_run_id or "").strip() or None,
        "candidate_key": str(candidate_key or "").strip(),
        "candidate_value": candidate_value,
        "reason": str(reason or "").strip(),
        "sensitivity": str(sensitivity or "medium").strip().lower(),
        "idempotency_key": str(idempotency_key or "").strip() or None,
        "version": 1,
        "created_at": now,
        "updated_at": now,
    }
