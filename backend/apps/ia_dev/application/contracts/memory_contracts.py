from __future__ import annotations

import re
from typing import Any


VALID_MEMORY_SCOPES = {"session", "user", "business", "workflow", "general"}
VALID_MEMORY_SENSITIVITY = {"low", "medium", "high"}
SAFE_MEMORY_KEY_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,120}$")


def normalize_scope(value: str | None, *, default: str = "user") -> str:
    item = str(value or "").strip().lower() or default
    return item if item in VALID_MEMORY_SCOPES else default


def normalize_sensitivity(value: str | None, *, default: str = "medium") -> str:
    item = str(value or "").strip().lower() or default
    return item if item in VALID_MEMORY_SENSITIVITY else default


def ensure_memory_proposal_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(payload or {})
    return {
        "scope": normalize_scope(raw.get("scope")),
        "candidate_key": str(raw.get("candidate_key") or "").strip(),
        "candidate_value": raw.get("candidate_value"),
        "reason": str(raw.get("reason") or "").strip(),
        "sensitivity": normalize_sensitivity(raw.get("sensitivity")),
        "idempotency_key": str(raw.get("idempotency_key") or "").strip() or None,
        "domain_code": str(raw.get("domain_code") or "").strip() or None,
        "capability_id": str(raw.get("capability_id") or "").strip() or None,
    }


def is_valid_memory_key(value: str | None) -> bool:
    key = str(value or "").strip()
    return bool(SAFE_MEMORY_KEY_RE.match(key))
