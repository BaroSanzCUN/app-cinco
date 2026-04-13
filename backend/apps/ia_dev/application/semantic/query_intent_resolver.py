from __future__ import annotations

import json
import os
import re
from datetime import date
from typing import Any

from apps.ia_dev.application.contracts.query_intelligence_contracts import StructuredQueryIntent
from apps.ia_dev.services.period_service import resolve_period_from_text


class QueryIntentResolver:
    """
    Traduce lenguaje natural a intencion estructurada.
    Prioriza reglas; opcionalmente refina con OpenAI usando contexto semantico.
    """

    def __init__(self):
        self.model = str(os.getenv("IA_DEV_QUERY_INTENT_MODEL", os.getenv("IA_DEV_MODEL", "gpt-5-nano")) or "gpt-5-nano")
        self.use_openai = str(os.getenv("IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED", "1") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    @staticmethod
    def _get_openai_api_key() -> str:
        return str(os.getenv("OPENAI_API_KEY") or os.getenv("IA_DEV_OPENAI_API_KEY") or "").strip()

    def resolve(
        self,
        *,
        message: str,
        base_classification: dict[str, Any],
        semantic_context: dict[str, Any] | None = None,
    ) -> StructuredQueryIntent:
        rules = self._resolve_rules(
            message=message,
            base_classification=base_classification,
        )
        if not self.use_openai:
            return rules

        api_key = self._get_openai_api_key()
        if not api_key:
            return rules

        try:
            llm = self._resolve_openai(
                message=message,
                api_key=api_key,
                fallback=rules,
                semantic_context=semantic_context or {},
            )
            return self._merge_intents(fallback=rules, llm=llm)
        except Exception:
            return rules

    def _resolve_rules(self, *, message: str, base_classification: dict[str, Any]) -> StructuredQueryIntent:
        normalized = self._normalize_text(message)
        domain = str(base_classification.get("domain") or "").strip().lower()
        if not domain:
            if any(token in normalized for token in ("ausent", "asistencia", "injustific")):
                domain = "ausentismo"
            elif any(token in normalized for token in ("emplead", "cedula", "rrhh", "activo")):
                domain = "empleados"
            else:
                domain = "general"

        operation = "summary"
        if any(token in normalized for token in ("cantidad", "cuantos", "cuantas", "total", "numero")):
            operation = "count"
        elif any(token in normalized for token in ("compar", "vs", "versus")):
            operation = "compare"
        elif any(token in normalized for token in ("tendencia", "historico", "evolucion", "trend")):
            operation = "trend"
        elif any(token in normalized for token in ("detalle", "tabla", "mostrar", "lista")):
            operation = "detail"

        template_id = self._resolve_template_id(
            normalized=normalized,
            domain_code=domain,
            operation=operation,
        )
        entity_type, entity_value = self._extract_entity(normalized=normalized)
        filters = self._extract_filters(normalized=normalized)
        if entity_type == "cedula" and entity_value:
            filters.setdefault("cedula", entity_value)
        if domain in {"empleados", "rrhh"} and "activo" in normalized:
            filters["estado"] = "ACTIVO"

        period = self._resolve_period_payload(message=message)
        group_by = self._extract_group_by(normalized=normalized)
        metrics = self._extract_metrics(normalized=normalized, operation=operation)

        return StructuredQueryIntent(
            raw_query=message,
            domain_code=domain,
            operation=operation,
            template_id=template_id,
            entity_type=entity_type,
            entity_value=entity_value,
            filters=filters,
            period=period,
            group_by=group_by,
            metrics=metrics,
            confidence=0.72,
            source="rules",
            warnings=[],
        )

    def _resolve_openai(
        self,
        *,
        message: str,
        api_key: str,
        fallback: StructuredQueryIntent,
        semantic_context: dict[str, Any],
    ) -> StructuredQueryIntent:
        from openai import OpenAI

        context_payload = self._compact_semantic_context(semantic_context=semantic_context)
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Eres un resolver de intencion estructurada para analytics empresarial.\n"
                        "Devuelve SOLO JSON con llaves: domain_code, operation, template_id, entity_type, entity_value, "
                        "filters, period, group_by, metrics, confidence.\n"
                        "template_id permitido: count_entities_by_status, count_records_by_period, "
                        "detail_by_entity_and_period, aggregate_by_group_and_period, trend_by_period.\n"
                        "operation permitido: count, detail, aggregate, trend, compare, summary.\n"
                        "No generes SQL, no agregues texto fuera del JSON."
                    ),
                },
                {
                    "role": "system",
                    "content": (
                        "Contexto semantico disponible (usar solo esta estructura para interpretar negocio):\n"
                        f"{json.dumps(context_payload, ensure_ascii=False)}"
                    ),
                },
                {"role": "user", "content": message},
            ],
        )
        raw_text = str(getattr(response, "output_text", "") or "").strip()
        payload = self._safe_json(raw_text)
        return StructuredQueryIntent(
            raw_query=message,
            domain_code=str(payload.get("domain_code") or fallback.domain_code or "").strip().lower(),
            operation=str(payload.get("operation") or fallback.operation or "summary").strip().lower(),
            template_id=str(payload.get("template_id") or fallback.template_id or "").strip().lower(),
            entity_type=str(payload.get("entity_type") or fallback.entity_type or "").strip().lower(),
            entity_value=str(payload.get("entity_value") or fallback.entity_value or "").strip(),
            filters=payload.get("filters") if isinstance(payload.get("filters"), dict) else dict(fallback.filters or {}),
            period=payload.get("period") if isinstance(payload.get("period"), dict) else dict(fallback.period or {}),
            group_by=payload.get("group_by") if isinstance(payload.get("group_by"), list) else list(fallback.group_by or []),
            metrics=payload.get("metrics") if isinstance(payload.get("metrics"), list) else list(fallback.metrics or []),
            confidence=float(payload.get("confidence") or fallback.confidence or 0.0),
            source="openai",
            warnings=[],
        )

    @staticmethod
    def _merge_intents(*, fallback: StructuredQueryIntent, llm: StructuredQueryIntent) -> StructuredQueryIntent:
        return StructuredQueryIntent(
            raw_query=fallback.raw_query,
            domain_code=str(llm.domain_code or fallback.domain_code or "").strip().lower(),
            operation=str(llm.operation or fallback.operation or "summary").strip().lower(),
            template_id=str(llm.template_id or fallback.template_id or "").strip().lower(),
            entity_type=str(llm.entity_type or fallback.entity_type or "").strip().lower(),
            entity_value=str(llm.entity_value or fallback.entity_value or "").strip(),
            filters=dict(llm.filters or fallback.filters or {}),
            period=dict(llm.period or fallback.period or {}),
            group_by=list(llm.group_by or fallback.group_by or []),
            metrics=list(llm.metrics or fallback.metrics or []),
            confidence=float(llm.confidence or fallback.confidence or 0.0),
            source=str(llm.source or "openai"),
            warnings=list(llm.warnings or []),
        )

    @staticmethod
    def _resolve_template_id(*, normalized: str, domain_code: str, operation: str) -> str:
        if domain_code in {"empleados", "rrhh"} and operation == "count" and "activo" in normalized:
            return "count_entities_by_status"
        if operation == "trend":
            return "trend_by_period"
        if operation == "detail" and re.search(r"\b\d{6,13}\b", normalized):
            return "detail_by_entity_and_period"
        if operation in {"aggregate", "compare", "summary"} and any(
            token in normalized for token in ("por supervisor", "por area", "por cargo")
        ):
            return "aggregate_by_group_and_period"
        if operation == "count":
            return "count_records_by_period"
        if operation == "detail":
            return "detail_by_entity_and_period"
        return "aggregate_by_group_and_period"

    @staticmethod
    def _extract_entity(*, normalized: str) -> tuple[str, str]:
        match = re.search(r"\b\d{6,13}\b", normalized)
        if not match:
            return "", ""
        return "cedula", "".join(ch for ch in match.group(0) if ch.isdigit())

    @staticmethod
    def _extract_filters(*, normalized: str) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if "activo" in normalized:
            filters["estado"] = "ACTIVO"
        if "inactivo" in normalized:
            filters["estado"] = "INACTIVO"
        return filters

    @staticmethod
    def _extract_group_by(*, normalized: str) -> list[str]:
        values: list[str] = []
        for item in ("supervisor", "area", "cargo", "carpeta"):
            if f"por {item}" in normalized or f"{item} " in normalized:
                values.append(item)
        return values

    @staticmethod
    def _extract_metrics(*, normalized: str, operation: str) -> list[str]:
        metrics: list[str] = []
        if operation == "count" or any(token in normalized for token in ("cantidad", "total", "cuantos", "cuantas")):
            metrics.append("count")
        if any(token in normalized for token in ("porcentaje", "participacion")):
            metrics.append("percentage")
        return metrics or ["count"]

    @staticmethod
    def _resolve_period_payload(*, message: str) -> dict[str, Any]:
        resolved = resolve_period_from_text(message)
        start = resolved.get("start")
        end = resolved.get("end")
        payload = {
            "label": str(resolved.get("label") or ""),
            "start_date": start.isoformat() if isinstance(start, date) else "",
            "end_date": end.isoformat() if isinstance(end, date) else "",
        }
        return payload

    @staticmethod
    def _compact_semantic_context(*, semantic_context: dict[str, Any]) -> dict[str, Any]:
        tables = []
        for item in list(semantic_context.get("tables") or [])[:6]:
            if not isinstance(item, dict):
                continue
            tables.append(
                {
                    "table_fqn": item.get("table_fqn"),
                    "table_name": item.get("table_name"),
                    "logical_name": item.get("nombre_tabla_logico"),
                    "role": item.get("rol"),
                }
            )
        columns = []
        for item in list(semantic_context.get("columns") or [])[:20]:
            if not isinstance(item, dict):
                continue
            columns.append(
                {
                    "table_name": item.get("table_name"),
                    "column_name": item.get("column_name"),
                    "logical_name": item.get("nombre_columna_logico"),
                }
            )
        relations = []
        for item in list(semantic_context.get("relationships") or [])[:10]:
            if not isinstance(item, dict):
                continue
            relations.append(
                {
                    "nombre_relacion": item.get("nombre_relacion"),
                    "condicion": item.get("condicion"),
                }
            )
        synonyms = []
        dictionary = dict(semantic_context.get("dictionary") or {})
        for item in list(dictionary.get("synonyms") or [])[:20]:
            if not isinstance(item, dict):
                continue
            synonyms.append(
                {
                    "termino": item.get("termino"),
                    "sinonimo": item.get("sinonimo"),
                }
            )
        return {
            "domain_code": semantic_context.get("domain_code"),
            "domain_status": semantic_context.get("domain_status"),
            "main_entity": semantic_context.get("main_entity"),
            "tables": tables,
            "columns": columns,
            "relationships": relations,
            "synonyms": synonyms,
            "allowed_tables": list(semantic_context.get("allowed_tables") or []),
            "allowed_columns": list(semantic_context.get("allowed_columns") or []),
            "flags": dict(semantic_context.get("flags") or {}),
        }

    @staticmethod
    def _safe_json(raw_text: str) -> dict[str, Any]:
        if not raw_text:
            return {}
        json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        raw = json_match.group(0) if json_match else raw_text
        try:
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _normalize_text(value: str) -> str:
        return str(value or "").strip().lower()
