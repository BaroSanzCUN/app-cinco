from __future__ import annotations

import re
import unicodedata
from typing import Any


class RuleSemanticResolver:
    """
    Resolver de reglas funcionales (dd_reglas + reglas base obligatorias).
    """

    _COUNT_TOKENS = ("cantidad", "cuantos", "cuantas", "total", "numero")
    _ACTIVE_TOKENS = ("activo", "activos")
    _INACTIVE_TOKENS = ("inactivo", "inactivos")

    @staticmethod
    def _normalize_text(value: str | None) -> str:
        lowered = str(value or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    def infer_operation(self, *, message: str, fallback: str = "summary") -> str:
        normalized = self._normalize_text(message)
        if any(token in normalized for token in self._COUNT_TOKENS):
            return "count"
        return str(fallback or "summary")

    def infer_identifier_from_message(
        self,
        *,
        message: str,
        domain_code: str,
    ) -> dict[str, str]:
        normalized = self._normalize_text(message)
        normalized_domain = self._normalize_text(domain_code)
        if normalized_domain not in {"empleados", "rrhh", "ausentismo", "attendance"} and not any(
            token in normalized for token in ("empleado", "colaborador", "personal", "ausentismo")
        ):
            return {}
        match = re.search(r"\b\d{6,13}\b", normalized)
        if not match:
            return {}
        return {"cedula": "".join(ch for ch in match.group(0) if ch.isdigit())}

    def normalize_status_value(
        self,
        *,
        raw_value: str | None,
        allowed_values: list[str] | None = None,
    ) -> str:
        value = self._normalize_text(raw_value)
        if not value:
            return ""
        if value in self._ACTIVE_TOKENS:
            candidate = "ACTIVO"
        elif value in self._INACTIVE_TOKENS:
            candidate = "INACTIVO"
        else:
            candidate = str(raw_value or "").strip().upper()

        allowed = {str(item or "").strip().upper() for item in list(allowed_values or []) if str(item or "").strip()}
        if not allowed:
            return candidate
        if candidate in allowed:
            return candidate
        if candidate.startswith("ACTIV") and "ACTIVO" in allowed:
            return "ACTIVO"
        if candidate.startswith("INACTIV") and "INACTIVO" in allowed:
            return "INACTIVO"
        return candidate

    def apply_rule_overrides(
        self,
        *,
        message: str,
        domain_code: str,
        filters: dict[str, Any],
        dictionary_rules: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        resolved = dict(filters or {})
        normalized = self._normalize_text(message)
        normalized_domain = self._normalize_text(domain_code)

        identifier_filter = self.infer_identifier_from_message(
            message=message,
            domain_code=normalized_domain,
        )
        for key, value in identifier_filter.items():
            resolved.setdefault(key, value)

        # Hook para reglas textuales de dd_reglas (modo conservador).
        for row in list(dictionary_rules or []):
            if not isinstance(row, dict):
                continue
            resultado = self._normalize_text(row.get("resultado_funcional"))
            if not resultado:
                continue
            if "empleado = cedula" in resultado and "cedula" not in resolved:
                resolved.update(identifier_filter)
            if "cantidad" in resultado and any(token in normalized for token in self._COUNT_TOKENS):
                resolved.setdefault("_operation_hint", "count")

        return resolved
