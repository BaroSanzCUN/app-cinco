from __future__ import annotations

from dataclasses import dataclass


VALID_SCOPES = {"session", "user", "business", "workflow", "general"}
VALID_SENSITIVITY = {"low", "medium", "high"}


@dataclass(slots=True)
class ScopeClassification:
    scope: str
    sensitivity: str
    confidence: float
    reason: str


class MemoryScopeClassifierTool:
    def classify(
        self,
        *,
        key: str,
        value_text: str,
        requested_scope: str | None = None,
    ) -> ScopeClassification:
        raw_scope = str(requested_scope or "").strip().lower()
        if raw_scope in VALID_SCOPES:
            sensitivity = self._guess_sensitivity(value_text)
            return ScopeClassification(
                scope=raw_scope,
                sensitivity=sensitivity,
                confidence=0.95,
                reason="requested_scope",
            )

        text = f"{key} {value_text}".strip().lower()
        if any(token in text for token in ("mi formato", "prefiero", "estilo", "mis filtros")):
            return ScopeClassification(
                scope="user",
                sensitivity=self._guess_sensitivity(text),
                confidence=0.8,
                reason="user_preference_keywords",
            )
        if any(token in text for token in ("global", "todos los dominios", "sistema completo")):
            return ScopeClassification(
                scope="general",
                sensitivity=self._guess_sensitivity(text),
                confidence=0.8,
                reason="global_keywords",
            )
        if any(token in text for token in ("regla funcional", "patron", "procedimiento", "dominio")):
            return ScopeClassification(
                scope="business",
                sensitivity=self._guess_sensitivity(text),
                confidence=0.75,
                reason="business_keywords",
            )
        return ScopeClassification(
            scope="user",
            sensitivity=self._guess_sensitivity(text),
            confidence=0.55,
            reason="default_user_scope",
        )

    @staticmethod
    def _guess_sensitivity(text: str) -> str:
        t = str(text or "").lower()
        high_tokens = ("password", "token", "secret", "api_key", "cedula", "documento", "correo")
        medium_tokens = ("telefono", "email", "supervisor", "cargo")
        if any(token in t for token in high_tokens):
            return "high"
        if any(token in t for token in medium_tokens):
            return "medium"
        return "low"
