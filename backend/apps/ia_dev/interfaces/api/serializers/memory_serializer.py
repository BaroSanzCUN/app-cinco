from __future__ import annotations

import json
import re
from typing import Any

from apps.ia_dev.application.contracts.memory_contracts import (
    VALID_MEMORY_SCOPES,
    VALID_MEMORY_SENSITIVITY,
)


_SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9_.:\-]{1,120}$")
_MAX_CANDIDATE_VALUE_BYTES = 8 * 1024
_MAX_REASON_BYTES = 4 * 1024


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def parse_limit(raw, *, default: int = 30, min_value: int = 1, max_value: int = 500) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(min_value, min(value, max_value))


def normalize_memory_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data or {})
    return {
        "scope": str(payload.get("scope") or "").strip().lower() or None,
        "candidate_key": str(payload.get("candidate_key") or "").strip(),
        "candidate_value": payload.get("candidate_value"),
        "reason": str(payload.get("reason") or "").strip(),
        "sensitivity": str(payload.get("sensitivity") or "").strip().lower() or None,
        "idempotency_key": str(payload.get("idempotency_key") or "").strip() or None,
        "domain_code": str(payload.get("domain_code") or "").strip() or None,
        "capability_id": str(payload.get("capability_id") or "").strip() or None,
        "direct_write": _to_bool(payload.get("direct_write", False)),
        "source_run_id": str(payload.get("source_run_id") or "").strip() or None,
    }


def validate_memory_payload(payload: dict[str, Any]) -> tuple[bool, str | None]:
    scope = str(payload.get("scope") or "").strip().lower()
    if scope and scope not in VALID_MEMORY_SCOPES:
        return False, f"scope invalido: {scope}"

    sensitivity = str(payload.get("sensitivity") or "").strip().lower()
    if sensitivity and sensitivity not in VALID_MEMORY_SENSITIVITY:
        return False, f"sensitivity invalida: {sensitivity}"

    key = str(payload.get("candidate_key") or "").strip()
    if not key:
        return False, "candidate_key is required"
    if not _SAFE_KEY_RE.match(key):
        return False, "candidate_key formato invalido (usa [A-Za-z0-9_.:-], max 120)"

    reason = str(payload.get("reason") or "")
    if len(reason.encode("utf-8")) > _MAX_REASON_BYTES:
        return False, "reason excede tamano permitido"

    try:
        raw_json = json.dumps(payload.get("candidate_value"), ensure_ascii=False)
    except Exception:
        return False, "candidate_value no es serializable"

    if len(raw_json.encode("utf-8")) > _MAX_CANDIDATE_VALUE_BYTES:
        return False, "candidate_value excede tamano permitido (8KB)"

    return True, None
