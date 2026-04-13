from __future__ import annotations

import re
from datetime import date
from typing import Any

from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    ResolvedQuerySpec,
    SatisfactionValidation,
)


class ResultSatisfactionValidator:
    def validate(
        self,
        *,
        message: str,
        response: dict[str, Any],
        resolved_query: ResolvedQuerySpec | None = None,
    ) -> SatisfactionValidation:
        normalized_message = self._normalize_text(message)
        data = dict((response or {}).get("data") or {})
        table = dict(data.get("table") or {})
        rows = list(table.get("rows") or [])
        kpis = dict(data.get("kpis") or {})
        checks: dict[str, Any] = {}

        expected_cedula = self._resolve_expected_cedula(normalized_message, resolved_query=resolved_query)
        if expected_cedula:
            row_cedulas = {
                self._normalize_identifier(str(item.get("cedula") or ""))
                for item in rows
                if isinstance(item, dict)
            }
            row_cedulas.discard("")
            checks["expected_cedula"] = expected_cedula
            checks["row_cedulas"] = sorted(row_cedulas)
            if row_cedulas and row_cedulas != {expected_cedula}:
                return SatisfactionValidation(
                    satisfied=False,
                    reason="entity_filter_not_applied_for_cedula",
                    checks=checks,
                )

        asks_count = any(token in normalized_message for token in ("cantidad", "cuantos", "cuantas", "total", "numero"))
        expected_template = str(((resolved_query.intent.template_id if resolved_query else "") or "")).strip().lower()
        if asks_count or expected_template.startswith("count_"):
            has_numeric_kpi = any(isinstance(value, (int, float)) for value in kpis.values())
            if not has_numeric_kpi and rows:
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    if any(isinstance(value, (int, float)) for value in row.values()):
                        has_numeric_kpi = True
                        break
            checks["has_numeric_kpi"] = has_numeric_kpi
            if not has_numeric_kpi:
                return SatisfactionValidation(
                    satisfied=False,
                    reason="count_requested_without_numeric_kpi",
                    checks=checks,
                )

        asks_grouped_count = asks_count and any(
            token in normalized_message
            for token in (
                "por supervisor",
                "por area",
                "por cargo",
                "por carpeta",
                "por justificacion",
                "por causa",
                "por motivo",
                "por tipo",
                "por estado",
            )
        )
        if asks_grouped_count and rows:
            detail_like = any("fecha_ausentismo" in row and "cedula" in row for row in rows if isinstance(row, dict))
            has_group_metric = any(
                any(metric in row for metric in ("total_injustificados", "total_ausentismos", "total_eventos", "cantidad"))
                for row in rows
                if isinstance(row, dict)
            )
            checks["grouped_count"] = {
                "detail_like": detail_like,
                "has_group_metric": has_group_metric,
            }
            if detail_like or not has_group_metric:
                return SatisfactionValidation(
                    satisfied=False,
                    reason="group_count_requested_but_result_is_not_aggregated",
                    checks=checks,
                )

        asks_active = "activo" in normalized_message or "activos" in normalized_message
        if asks_active:
            reply = str((response or {}).get("reply") or "").lower()
            checks["asks_active"] = True
            checks["reply_mentions_active"] = "activo" in reply
            # No bloquear por redaccion textual, solo registrar.

        asks_last_year = bool(re.search(r"\b(ultimo|ultimos|ultima|ultimas)\s+ano(s)?\b", normalized_message))
        if asks_last_year:
            period = self._extract_period_from_response(response=response)
            checks["resolved_period"] = period
            if period:
                start, end = period
                if (end - start).days < 330:
                    return SatisfactionValidation(
                        satisfied=False,
                        reason="period_for_last_year_is_too_short",
                        checks=checks,
                    )

        expected_period = dict((resolved_query.normalized_period if resolved_query else {}) or {})
        expected_start = str(expected_period.get("start_date") or "")
        expected_end = str(expected_period.get("end_date") or "")
        if expected_start and expected_end:
            checks["expected_period"] = {"start_date": expected_start, "end_date": expected_end}

        return SatisfactionValidation(
            satisfied=True,
            reason="ok",
            checks=checks,
        )

    @staticmethod
    def _resolve_expected_cedula(message: str, *, resolved_query: ResolvedQuerySpec | None) -> str:
        if resolved_query is not None:
            value = resolved_query.normalized_filters.get("cedula")
            normalized = ResultSatisfactionValidator._normalize_identifier(str(value or ""))
            if normalized:
                return normalized
        match = re.search(r"\b\d{6,13}\b", str(message or ""))
        if not match:
            return ""
        return ResultSatisfactionValidator._normalize_identifier(match.group(0))

    @staticmethod
    def _extract_period_from_response(*, response: dict[str, Any]) -> tuple[date, date] | None:
        reply = str((response or {}).get("reply") or "").lower()
        match = re.search(r"periodo\s+(\d{4}-\d{2}-\d{2})\s+al\s+(\d{4}-\d{2}-\d{2})", reply)
        if match:
            try:
                return date.fromisoformat(match.group(1)), date.fromisoformat(match.group(2))
            except Exception:
                return None

        table = dict((dict((response or {}).get("data") or {})).get("table") or {})
        rows = list(table.get("rows") or [])
        if rows and isinstance(rows[0], dict):
            first = rows[0]
            if first.get("periodo_inicio") and first.get("periodo_fin"):
                try:
                    return date.fromisoformat(str(first.get("periodo_inicio"))), date.fromisoformat(str(first.get("periodo_fin")))
                except Exception:
                    return None
        return None

    @staticmethod
    def _normalize_identifier(value: str) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    @staticmethod
    def _normalize_text(value: str) -> str:
        return str(value or "").strip().lower()
