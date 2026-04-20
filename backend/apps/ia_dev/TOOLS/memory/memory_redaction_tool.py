from __future__ import annotations

import re
from typing import Any


class MemoryRedactionTool:
    _REPLACEMENTS = (
        (re.compile(r"(api[_-]?key\s*[:=]\s*)[^\s,;]+", re.IGNORECASE), r"\1[REDACTED]"),
        (re.compile(r"(token\s*[:=]\s*)[^\s,;]+", re.IGNORECASE), r"\1[REDACTED]"),
        (re.compile(r"(password\s*[:=]\s*)[^\s,;]+", re.IGNORECASE), r"\1[REDACTED]"),
    )

    def redact_text(self, text: str) -> str:
        value = str(text or "")
        for pattern, replacement in self._REPLACEMENTS:
            value = pattern.sub(replacement, value)
        return value

    def redact_payload(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            return {k: self.redact_payload(v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [self.redact_payload(item) for item in payload]
        if isinstance(payload, str):
            return self.redact_text(payload)
        return payload
