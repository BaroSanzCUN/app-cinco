from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StructuredQueryIntent:
    raw_query: str
    domain_code: str
    operation: str
    template_id: str
    entity_type: str = ""
    entity_value: str = ""
    filters: dict[str, Any] = field(default_factory=dict)
    period: dict[str, Any] = field(default_factory=dict)
    group_by: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source: str = "rules"
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "raw_query": str(self.raw_query or ""),
            "domain_code": str(self.domain_code or ""),
            "operation": str(self.operation or ""),
            "template_id": str(self.template_id or ""),
            "entity_type": str(self.entity_type or ""),
            "entity_value": str(self.entity_value or ""),
            "filters": dict(self.filters or {}),
            "period": dict(self.period or {}),
            "group_by": list(self.group_by or []),
            "metrics": list(self.metrics or []),
            "confidence": float(self.confidence or 0.0),
            "source": str(self.source or "rules"),
            "warnings": list(self.warnings or []),
        }


@dataclass(slots=True)
class ResolvedQuerySpec:
    intent: StructuredQueryIntent
    semantic_context: dict[str, Any] = field(default_factory=dict)
    normalized_filters: dict[str, Any] = field(default_factory=dict)
    normalized_period: dict[str, Any] = field(default_factory=dict)
    mapped_columns: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.as_dict(),
            "semantic_context": dict(self.semantic_context or {}),
            "normalized_filters": dict(self.normalized_filters or {}),
            "normalized_period": dict(self.normalized_period or {}),
            "mapped_columns": dict(self.mapped_columns or {}),
            "warnings": list(self.warnings or []),
        }


@dataclass(slots=True)
class QueryExecutionPlan:
    strategy: str
    reason: str
    domain_code: str
    capability_id: str | None = None
    sql_query: str | None = None
    requires_context: bool = False
    missing_context: list[str] = field(default_factory=list)
    policy: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "strategy": str(self.strategy or ""),
            "reason": str(self.reason or ""),
            "domain_code": str(self.domain_code or ""),
            "capability_id": self.capability_id,
            "sql_query": self.sql_query,
            "requires_context": bool(self.requires_context),
            "missing_context": list(self.missing_context or []),
            "policy": dict(self.policy or {}),
            "metadata": dict(self.metadata or {}),
        }


@dataclass(slots=True)
class SatisfactionValidation:
    satisfied: bool
    reason: str
    checks: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "satisfied": bool(self.satisfied),
            "reason": str(self.reason or ""),
            "checks": dict(self.checks or {}),
        }


@dataclass(slots=True)
class QueryPatternMemory:
    scope: str
    candidate_key: str
    candidate_value: dict[str, Any]
    reason: str
    sensitivity: str = "low"
    domain_code: str = ""
    capability_id: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "scope": str(self.scope or "user"),
            "candidate_key": str(self.candidate_key or ""),
            "candidate_value": dict(self.candidate_value or {}),
            "reason": str(self.reason or ""),
            "sensitivity": str(self.sensitivity or "low"),
            "domain_code": str(self.domain_code or ""),
            "capability_id": str(self.capability_id or ""),
        }
