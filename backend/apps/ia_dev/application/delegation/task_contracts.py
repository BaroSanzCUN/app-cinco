from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_task_id(prefix: str = "task") -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


@dataclass(slots=True)
class EntityScope:
    entity_type: str = "empresa"
    entity_ids: list[str] = field(default_factory=list)
    entity_attributes: dict[str, Any] = field(default_factory=dict)
    period_start: str | None = None
    period_end: str | None = None
    period_label: str | None = None
    business_filters: dict[str, Any] = field(default_factory=dict)
    group_by: list[str] = field(default_factory=list)
    metric_targets: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        merged_filters = {
            **dict(self.business_filters or {}),
            **dict(self.filters or {}),
        }
        return {
            "entity_type": str(self.entity_type or "empresa"),
            "entity_ids": list(self.entity_ids or []),
            "entity_attributes": dict(self.entity_attributes or {}),
            "period_start": self.period_start,
            "period_end": self.period_end,
            "period_label": self.period_label,
            "business_filters": dict(self.business_filters or {}),
            "filters": merged_filters,
            "group_by": list(self.group_by or []),
            "metric_targets": list(self.metric_targets or []),
        }


@dataclass(slots=True)
class DelegationTask:
    task_id: str
    run_id: str
    domain_code: str
    domain_status: str
    task_type: str
    capability_id: str | None = None
    capability: str | None = None
    business_method: str | None = None
    priority: int = 50
    depends_on: list[str] = field(default_factory=list)
    requested_outputs: list[str] = field(default_factory=list)
    business_objective: str = ""
    entity_scope: EntityScope = field(default_factory=EntityScope)
    constraints: dict[str, Any] = field(default_factory=dict)
    trace_context: dict[str, Any] = field(default_factory=dict)
    execution_strategy: str = "typed_tools"
    created_at: str = field(default_factory=_utc_now_iso)

    def as_dict(self) -> dict[str, Any]:
        capability = str(self.capability or self.capability_id or "").strip() or None
        period = {
            "start_date": self.entity_scope.period_start,
            "end_date": self.entity_scope.period_end,
            "label": self.entity_scope.period_label,
        }
        return {
            "task_id": self.task_id,
            "run_id": self.run_id,
            "domain_code": self.domain_code,
            "domain_status": self.domain_status,
            "task_type": self.task_type,
            "capability_id": self.capability_id,
            "capability": capability,
            "business_method": self.business_method,
            "priority": int(self.priority),
            "depends_on": list(self.depends_on or []),
            "requested_outputs": list(self.requested_outputs or []),
            "business_objective": self.business_objective,
            "entity_scope": self.entity_scope.as_dict(),
            "filters": dict(self.entity_scope.as_dict().get("filters") or {}),
            "period": period,
            "constraints": dict(self.constraints or {}),
            "trace_context": dict(self.trace_context or {}),
            "execution_strategy": str(self.execution_strategy or "typed_tools"),
            "created_at": self.created_at,
        }


@dataclass(slots=True)
class DelegationResult:
    task_id: str
    domain_code: str
    status: str
    reply_text: str = ""
    kpis: dict[str, Any] = field(default_factory=dict)
    table: dict[str, Any] = field(default_factory=dict)
    series: list[Any] = field(default_factory=list)
    labels: list[Any] = field(default_factory=list)
    chart: dict[str, Any] = field(default_factory=dict)
    insights: list[str] = field(default_factory=list)
    data_lineage: dict[str, Any] = field(default_factory=dict)
    policy_decisions: list[dict[str, Any]] = field(default_factory=list)
    trace_events: list[dict[str, Any]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)
    error_code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "domain_code": self.domain_code,
            "status": self.status,
            "reply_text": self.reply_text,
            "kpis": dict(self.kpis or {}),
            "table": dict(self.table or {}),
            "series": list(self.series or []),
            "labels": list(self.labels or []),
            "chart": dict(self.chart or {}),
            "insights": list(self.insights or []),
            "data_lineage": dict(self.data_lineage or {}),
            "policy_decisions": list(self.policy_decisions or []),
            "trace_events": list(self.trace_events or []),
            "actions": list(self.actions or []),
            "error_code": self.error_code,
        }


@dataclass(slots=True)
class AggregatedResponse:
    reply: str = ""
    sections: list[dict[str, Any]] = field(default_factory=list)
    kpis: dict[str, Any] = field(default_factory=dict)
    table: dict[str, Any] = field(default_factory=dict)
    series: list[Any] = field(default_factory=list)
    labels: list[Any] = field(default_factory=list)
    chart: dict[str, Any] = field(default_factory=dict)
    charts: list[dict[str, Any]] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    actions: list[dict[str, Any]] = field(default_factory=list)

    def as_payload(self) -> dict[str, Any]:
        charts_payload = list(self.charts or [])
        if self.chart and not charts_payload:
            charts_payload = [dict(self.chart)]
        payload: dict[str, Any] = {
            "reply": str(self.reply or ""),
            "sections": list(self.sections or []),
            "data": {
                "kpis": dict(self.kpis or {}),
                "table": dict(self.table or {}),
                "series": list(self.series or []),
                "labels": list(self.labels or []),
                "insights": list(self.insights or []),
                "charts": charts_payload,
            },
            "trace": list(self.trace or []),
            "actions": list(self.actions or []),
        }
        if self.chart:
            payload["data"]["chart"] = dict(self.chart)
        elif charts_payload:
            payload["data"]["chart"] = dict(charts_payload[0])
        return payload
