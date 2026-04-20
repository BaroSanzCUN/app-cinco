from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
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
        if not self._flag_enabled("IA_DEV_QUERY_PATTERN_MEMORY_ENABLED", "1"):
            return {"enabled": False, "saved": False}
        if not validation.satisfied:
            return {"enabled": True, "saved": False, "reason": validation.reason}
        if not self._flag_enabled("IA_DEV_MEMORY_PROPOSALS_ENABLED", "1"):
            return {
                "enabled": True,
                "saved": False,
                "reason": "memory_proposals_disabled",
                "flag": "IA_DEV_MEMORY_PROPOSALS_ENABLED",
            }

        domain_code = str(resolved_query.intent.domain_code or "general").strip().upper()
        template_id = str(resolved_query.intent.template_id or "unknown").strip().lower()
        capability_id = str(execution_plan.capability_id or execution_plan.metadata.get("capability_id") or "").strip()
        satisfaction_score = self._compute_satisfaction_score(validation=validation)
        min_score = self._min_score_threshold()
        if satisfaction_score < min_score:
            return {
                "enabled": True,
                "saved": False,
                "reason": "satisfaction_score_below_threshold",
                "score": satisfaction_score,
                "min_score": min_score,
            }
        identifiers = self._extract_identifier_filters(
            normalized_filters=dict(resolved_query.normalized_filters or {}),
            execution_constraints=dict(execution_plan.constraints or {}),
        )
        pattern_value = self._build_pattern_value(
            resolved_query=resolved_query,
            execution_plan=execution_plan,
            validation=validation,
            satisfaction_score=satisfaction_score,
            response=response,
            scope="user",
        )
        sensitivity = self._infer_sensitivity(
            normalized_filters=dict(resolved_query.normalized_filters or {}),
            identifiers=identifiers,
        )
        user_scope_enabled = self._flag_enabled("IA_DEV_QUERY_PATTERN_MEMORY_USER_ENABLED", "1")
        effective_user_scope_enabled = bool(user_scope_enabled and user_key)
        business_scope_enabled = self._flag_enabled(
            "IA_DEV_QUERY_PATTERN_MEMORY_BUSINESS_ENABLED",
            "1",
        )
        business_scope_allowed = bool(business_scope_enabled and not identifiers)

        if not effective_user_scope_enabled and not business_scope_allowed:
            return {
                "enabled": True,
                "saved": False,
                "reason": "query_pattern_memory_scope_disabled",
                "user_scope_enabled": effective_user_scope_enabled,
                "business_scope_allowed": business_scope_allowed,
            }

        result = None
        if effective_user_scope_enabled:
            pattern = QueryPatternMemory(
                scope="user",
                candidate_key=f"query.pattern.{domain_code.lower()}.{template_id}",
                candidate_value=pattern_value,
                reason="query_intelligence_success_pattern",
                sensitivity=sensitivity,
                domain_code=domain_code,
                capability_id=capability_id or "query.execution",
            )
            idempotency_key = self._idempotency_key(
                user_key=user_key,
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
        else:
            result = {"ok": False, "error": "user_scope_disabled"}

        business_result = None
        if business_scope_allowed:
            business_value = self._build_pattern_value(
                resolved_query=resolved_query,
                execution_plan=execution_plan,
                validation=validation,
                satisfaction_score=satisfaction_score,
                response=response,
                scope="business",
            )
            business_pattern = QueryPatternMemory(
                scope="business",
                candidate_key=f"query.pattern.domain.{domain_code.lower()}.{template_id}",
                candidate_value=business_value,
                reason="query_intelligence_domain_pattern",
                sensitivity="medium",
                domain_code=domain_code,
                capability_id=capability_id or "query.execution",
            )
            business_idempotency = self._idempotency_key(
                user_key=user_key,
                pattern=business_pattern,
            )
            business_result = self.memory_writer.create_proposal(
                user_key=user_key or "system_query_pattern_runtime",
                payload={
                    **business_pattern.as_dict(),
                    "idempotency_key": business_idempotency,
                    "direct_write": False,
                },
                source_run_id=run_context.run_id,
            )
            business_result = self._autoapply_business_pattern_if_safe(
                result=business_result,
                fallback_actor=user_key or "system_query_pattern_runtime",
            )
        elif business_scope_enabled and identifiers:
            business_result = {
                "ok": False,
                "error": "business_scope_blocked_by_identifiers",
                "identifiers": sorted(identifiers),
            }

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
                "satisfaction_score": satisfaction_score,
                "min_score": min_score,
                "user_scope_enabled": effective_user_scope_enabled,
                "business_scope_allowed": business_scope_allowed,
            },
            )
        return {
            "enabled": True,
            "saved": bool(result.get("ok")) or bool((business_result or {}).get("ok")),
            "result": result,
            "business_result": business_result,
            "score": satisfaction_score,
            "min_score": min_score,
        }

    def _autoapply_business_pattern_if_safe(
        self,
        *,
        result: dict[str, Any],
        fallback_actor: str,
    ) -> dict[str, Any]:
        payload = dict(result or {})
        if not self._flag_enabled("IA_DEV_QUERY_PATTERN_MEMORY_BUSINESS_AUTOAPPLY_ENABLED", "1"):
            return payload
        if not bool(payload.get("ok")):
            return payload
        proposal = dict(payload.get("proposal") or {})
        proposal_id = str(proposal.get("proposal_id") or "").strip()
        status = str(proposal.get("status") or "").strip().lower()
        if not proposal_id or status not in {"pending", "approved"}:
            return payload
        apply_result = self.memory_writer.approve_proposal(
            proposal_id=proposal_id,
            actor_user_key=str(fallback_actor or "system_query_pattern_runtime"),
            actor_role="system",
            comment="auto_apply_business_query_pattern_low_risk",
        )
        if bool(apply_result.get("ok")):
            payload["proposal"] = dict(apply_result.get("proposal") or proposal)
            payload["auto_applied"] = True
        return payload

    @staticmethod
    def _idempotency_key(*, user_key: str, pattern: QueryPatternMemory) -> str:
        raw = json.dumps(
            {
                "user_key": user_key,
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
    def _min_score_threshold() -> float:
        raw = str(os.getenv("IA_DEV_QUERY_PATTERN_MEMORY_MIN_SCORE", "0.75") or "0.75").strip()
        try:
            value = float(raw)
        except ValueError:
            value = 0.75
        return max(0.0, min(value, 1.0))

    @staticmethod
    def _compute_satisfaction_score(*, validation: SatisfactionValidation) -> float:
        if not bool(validation.satisfied):
            return 0.0
        checks = dict(validation.checks or {})
        score = 1.0
        if checks.get("expected_period") and checks.get("resolved_period_from_response") in {None, ""}:
            score -= 0.15
        if checks.get("expected_cedula") and not list(checks.get("row_cedulas") or []):
            score -= 0.2
        if checks.get("expected_group_by") and not str(checks.get("matched_group_dimension") or "").strip():
            score -= 0.2
        if checks.get("chart_requested") and not bool(checks.get("has_chart_payload")):
            score = min(score, 0.1)
        return max(0.0, min(score, 1.0))

    @staticmethod
    def _extract_identifier_filters(
        *,
        normalized_filters: dict[str, Any],
        execution_constraints: dict[str, Any],
    ) -> set[str]:
        values: set[str] = set()
        sources = [
            dict(normalized_filters or {}),
            dict((execution_constraints or {}).get("filters") or {}),
        ]
        for payload in sources:
            for key, value in payload.items():
                normalized_key = str(key or "").strip().lower()
                text = str(value or "").strip()
                if normalized_key in {"cedula", "identificacion", "documento", "id_empleado"} and text:
                    values.add(re.sub(r"\D", "", text))
        values.discard("")
        return values

    @staticmethod
    def _infer_sensitivity(*, normalized_filters: dict[str, Any], identifiers: set[str]) -> str:
        if identifiers:
            return "medium"
        filter_keys = {str(key or "").strip().lower() for key in dict(normalized_filters or {}).keys()}
        if filter_keys.intersection({"cedula", "documento", "identificacion", "id_empleado", "nombre"}):
            return "medium"
        return "low"

    def _build_pattern_value(
        self,
        *,
        resolved_query: ResolvedQuerySpec,
        execution_plan: QueryExecutionPlan,
        validation: SatisfactionValidation,
        satisfaction_score: float,
        response: dict[str, Any],
        scope: str,
    ) -> dict[str, Any]:
        filters = dict(resolved_query.normalized_filters or {})
        constraints = dict(execution_plan.constraints or {})
        scope_value = str(scope or "").strip().lower()
        if scope_value == "business":
            filters = self._sanitize_filters_for_business(filters=filters)
            constraints = self._sanitize_constraints_for_business(constraints=constraints)

        resolved_semantic = dict((resolved_query.semantic_context or {}).get("resolved_semantic") or {})
        semantic_signature = {
            "synonyms": list(resolved_semantic.get("synonyms") or [])[:10],
            "columns": list(resolved_semantic.get("columns") or [])[:20],
            "relations": list(resolved_semantic.get("relations") or [])[:10],
        }
        checks = dict(validation.checks or {})
        checks_excerpt = {
            "expected_period": checks.get("expected_period"),
            "expected_group_by": checks.get("expected_group_by"),
            "expected_cedula": checks.get("expected_cedula"),
            "matched_group_dimension": checks.get("matched_group_dimension"),
        }

        return {
            "domain_code": str(resolved_query.intent.domain_code or "").strip().upper(),
            "template_id": str(resolved_query.intent.template_id or "").strip().lower(),
            "operation": str(resolved_query.intent.operation or "").strip().lower(),
            "entity_type": str(resolved_query.intent.entity_type or "").strip().lower(),
            "surface_pattern": {
                "normalized_query": self._normalize_query_text(str(resolved_query.intent.raw_query or "")),
                "query_shape_key": self._build_query_shape_key(str(resolved_query.intent.raw_query or "")),
            },
            "semantic_pattern": {
                "filters": filters,
                "group_by": list(resolved_query.intent.group_by or []),
                "metrics": list(resolved_query.intent.metrics or []),
                "period": dict(resolved_query.normalized_period or {}),
                "semantic_signature": semantic_signature,
            },
            "execution_pattern": {
                "strategy": str(execution_plan.strategy or "").strip().lower(),
                "capability_id": str(execution_plan.capability_id or "").strip(),
                "constraints": constraints,
            },
            "satisfaction": {
                "satisfied": bool(validation.satisfied),
                "reason": str(validation.reason or ""),
                "score": satisfaction_score,
                "checks_excerpt": checks_excerpt,
            },
            "response_signature": self._response_signature(response=response),
        }

    @staticmethod
    def _sanitize_filters_for_business(*, filters: dict[str, Any]) -> dict[str, Any]:
        redacted: dict[str, Any] = {}
        for key, value in dict(filters or {}).items():
            normalized = str(key or "").strip().lower()
            if normalized in {"cedula", "documento", "identificacion", "id_empleado", "nombre"}:
                continue
            redacted[key] = value
        return redacted

    @staticmethod
    def _sanitize_constraints_for_business(*, constraints: dict[str, Any]) -> dict[str, Any]:
        payload = dict(constraints or {})
        filters = dict(payload.get("filters") or {})
        payload["filters"] = QueryPatternMemoryService._sanitize_filters_for_business(filters=filters)
        return payload

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
    def _normalize_query_text(value: str) -> str:
        lowered = str(value or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    @classmethod
    def _build_query_shape_key(cls, raw_query: str) -> str:
        normalized = cls._normalize_query_text(raw_query)
        normalized = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "<fecha>", normalized)
        normalized = re.sub(r"\b\d{6,13}\b", "<cedula>", normalized)
        normalized = re.sub(r"\b[a-z][a-z0-9_-]*\d+[a-z0-9_-]*\b", "<codigo>", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    @staticmethod
    def _record_event(*, observability, event_type: str, source: str, meta: dict[str, Any]) -> None:
        if observability is None or not hasattr(observability, "record_event"):
            return
        observability.record_event(
            event_type=event_type,
            source=source,
            meta=dict(meta or {}),
        )
