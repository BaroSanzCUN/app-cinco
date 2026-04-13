from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    QueryExecutionPlan,
    QueryPatternMemory,
    ResolvedQuerySpec,
    SatisfactionValidation,
)
from apps.ia_dev.application.memory.memory_write_service import MemoryWriteService


class QueryPatternMemoryService:
    def __init__(self, *, memory_writer: MemoryWriteService | None = None):
        self.memory_writer = memory_writer or MemoryWriteService()

    @staticmethod
    def _flag_enabled(name: str, default: str = "0") -> bool:
        raw = str(os.getenv(name, default) or "").strip().lower()
        return raw in {"1", "true", "yes", "on"}

    def record_success(
        self,
        *,
        user_key: str | None,
        resolved_query: ResolvedQuerySpec,
        execution_plan: QueryExecutionPlan,
        validation: SatisfactionValidation,
        run_context: RunContext,
        response: dict[str, Any],
        observability=None,
    ) -> dict[str, Any]:
        if not self._flag_enabled("IA_DEV_QUERY_PATTERN_MEMORY_ENABLED", "0"):
            return {"enabled": False, "saved": False}
        if not user_key:
            return {"enabled": True, "saved": False, "reason": "missing_user_key"}
        if not validation.satisfied:
            return {"enabled": True, "saved": False, "reason": validation.reason}

        domain_code = str(resolved_query.intent.domain_code or "general").strip().upper()
        template_id = str(resolved_query.intent.template_id or "unknown").strip().lower()
        capability_id = str(execution_plan.capability_id or execution_plan.metadata.get("capability_id") or "").strip()
        pattern_value = {
            "domain_code": domain_code,
            "template_id": template_id,
            "operation": str(resolved_query.intent.operation or ""),
            "normalized_filters": dict(resolved_query.normalized_filters or {}),
            "normalized_period": dict(resolved_query.normalized_period or {}),
            "strategy": str(execution_plan.strategy or ""),
            "capability_id": capability_id,
            "quality": {
                "satisfied": bool(validation.satisfied),
                "reason": str(validation.reason or ""),
                "checks": dict(validation.checks or {}),
            },
            "response_signature": self._response_signature(response=response),
        }

        pattern = QueryPatternMemory(
            scope="user",
            candidate_key=f"query.pattern.{domain_code.lower()}.{template_id}",
            candidate_value=pattern_value,
            reason="query_intelligence_success_pattern",
            sensitivity="low",
            domain_code=domain_code,
            capability_id=capability_id or "query.execution",
        )
        idempotency_key = self._idempotency_key(
            run_id=run_context.run_id,
            pattern=pattern,
        )
        result = self.memory_writer.create_proposal(
            user_key=user_key,
            payload={
                **pattern.as_dict(),
                "idempotency_key": idempotency_key,
                "direct_write": False,
            },
            source_run_id=run_context.run_id,
        )

        business_result = None
        if self._flag_enabled("IA_DEV_QUERY_PATTERN_MEMORY_BUSINESS_ENABLED", "0"):
            business_pattern = QueryPatternMemory(
                scope="business",
                candidate_key=f"query.pattern.domain.{domain_code.lower()}.{template_id}",
                candidate_value=pattern_value,
                reason="query_intelligence_domain_pattern",
                sensitivity="medium",
                domain_code=domain_code,
                capability_id=capability_id or "query.execution",
            )
            business_idempotency = self._idempotency_key(
                run_id=run_context.run_id,
                pattern=business_pattern,
            )
            business_result = self.memory_writer.create_proposal(
                user_key=user_key,
                payload={
                    **business_pattern.as_dict(),
                    "idempotency_key": business_idempotency,
                    "direct_write": False,
                },
                source_run_id=run_context.run_id,
            )

        self._record_event(
            observability=observability,
            event_type="query_pattern_memory_recorded",
            source="QueryPatternMemoryService",
            meta={
                "run_id": run_context.run_id,
                "trace_id": run_context.trace_id,
                "domain_code": domain_code,
                "template_id": template_id,
                "strategy": execution_plan.strategy,
                "result_ok": bool(result.get("ok")),
                "business_result_ok": bool((business_result or {}).get("ok")),
            },
        )
        return {
            "enabled": True,
            "saved": bool(result.get("ok")),
            "result": result,
            "business_result": business_result,
        }

    @staticmethod
    def _idempotency_key(*, run_id: str, pattern: QueryPatternMemory) -> str:
        raw = json.dumps(
            {
                "run_id": run_id,
                "candidate_key": pattern.candidate_key,
                "candidate_value": pattern.candidate_value,
                "scope": pattern.scope,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]
        return f"qipattern-{digest}"

    @staticmethod
    def _response_signature(*, response: dict[str, Any]) -> dict[str, Any]:
        data = dict((response or {}).get("data") or {})
        table = dict(data.get("table") or {})
        kpis = dict(data.get("kpis") or {})
        return {
            "kpi_keys": sorted([str(key) for key in kpis.keys()])[:20],
            "table_columns": list(table.get("columns") or [])[:20],
            "rowcount": int(table.get("rowcount") or 0),
        }

    @staticmethod
    def _record_event(*, observability, event_type: str, source: str, meta: dict[str, Any]) -> None:
        if observability is None or not hasattr(observability, "record_event"):
            return
        observability.record_event(
            event_type=event_type,
            source=source,
            meta=dict(meta or {}),
        )
