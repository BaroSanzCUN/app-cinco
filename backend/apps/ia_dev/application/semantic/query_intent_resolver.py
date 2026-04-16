from __future__ import annotations

import json
import os
import re
import unicodedata
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

    @staticmethod
    def _get_openai_api_key() -> str:
        return str(os.getenv("OPENAI_API_KEY") or os.getenv("IA_DEV_OPENAI_API_KEY") or "").strip()

    @staticmethod
    def _openai_enabled() -> bool:
        return str(os.getenv("IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED", "1") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

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
        if not self._openai_enabled():
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
        domain = self._resolve_domain(
            normalized=normalized,
            base_domain=str(base_classification.get("domain") or "").strip().lower(),
        )

        operation = "summary"
        if any(token in normalized for token in ("cantidad", "cuantos", "cuantas", "total", "numero")):
            operation = "count"
        elif any(token in normalized for token in ("compar", "vs", "versus")):
            operation = "compare"
        elif self._has_aggregate_signal(normalized):
            operation = "aggregate"
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
        llm_filters = dict(llm.filters or {})
        fallback_filters = dict(fallback.filters or {})
        llm_period = dict(llm.period or {})
        fallback_period = dict(fallback.period or {})
        llm_group_by = [str(item).strip().lower() for item in list(llm.group_by or []) if str(item).strip()]
        fallback_group_by = [str(item).strip().lower() for item in list(fallback.group_by or []) if str(item).strip()]
        merged_group_by = list(dict.fromkeys([*llm_group_by, *fallback_group_by]))

        operation = str(llm.operation or fallback.operation or "summary").strip().lower()
        template_id = str(llm.template_id or fallback.template_id or "").strip().lower()
        has_entity = bool(str(llm.entity_value or fallback.entity_value or "").strip()) or bool(
            str(llm_filters.get("cedula") or fallback_filters.get("cedula") or "").strip()
        )
        if operation == "detail" and not has_entity and str(fallback.operation or "").strip().lower() != "detail":
            operation = str(fallback.operation or "summary").strip().lower()
        if template_id == "detail_by_entity_and_period" and not has_entity and str(fallback.template_id or "").strip():
            template_id = str(fallback.template_id or "").strip().lower()

        llm_start = str(llm_period.get("start_date") or "").strip()
        llm_end = str(llm_period.get("end_date") or "").strip()
        fallback_start = str(fallback_period.get("start_date") or "").strip()
        fallback_end = str(fallback_period.get("end_date") or "").strip()
        llm_label = str(llm_period.get("label") or "").strip().lower()
        fallback_label = str(fallback_period.get("label") or "").strip().lower()
        if (
            fallback_start
            and fallback_end
            and fallback_label not in {"", "hoy"}
            and (
                not llm_start
                or not llm_end
                or (llm_label == "hoy" and llm_start == llm_end)
            )
        ):
            llm_period = fallback_period

        return StructuredQueryIntent(
            raw_query=fallback.raw_query,
            domain_code=str(llm.domain_code or fallback.domain_code or "").strip().lower(),
            operation=operation,
            template_id=template_id,
            entity_type=str(llm.entity_type or fallback.entity_type or "").strip().lower(),
            entity_value=str(llm.entity_value or fallback.entity_value or "").strip(),
            filters=llm_filters or fallback_filters,
            period=llm_period or fallback_period,
            group_by=merged_group_by,
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
        if operation in {"aggregate", "compare", "summary"} and QueryIntentResolver._has_group_dimension_signal(normalized):
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
        estado_match = re.search(
            r"\bestado(?:\s+del?\s+\w+)?\s+(?:es\s+)?([a-z_]+)\b",
            str(normalized or ""),
        )
        if estado_match:
            filters["estado"] = str(estado_match.group(1) or "").strip().upper()
        return filters

    @staticmethod
    def _extract_group_by(*, normalized: str) -> list[str]:
        values: list[str] = []
        variants = {
            "supervisor": ("supervisor", "supervisores", "jefe", "jefes", "lider", "lideres"),
            "area": ("area", "areas"),
            "cargo": ("cargo", "cargos"),
            "carpeta": ("carpeta", "carpetas"),
        }
        for canonical, tokens in variants.items():
            if any(f"por {token}" in normalized for token in tokens):
                values.append(canonical)
                continue
            if any(re.search(rf"\b{re.escape(token)}\b", normalized) for token in tokens):
                values.append(canonical)
        return list(dict.fromkeys(values))

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
        lowered = str(value or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    @staticmethod
    def _resolve_domain(*, normalized: str, base_domain: str) -> str:
        domain = str(base_domain or "").strip().lower()
        if domain in {"ausentismo", "attendance", "empleados", "rrhh", "transporte", "transport"}:
            return domain

        rrhh_match = bool(
            re.search(
                r"\b(colaborador(?:es)?|usuario(?:s)?|emplead\w*|cedula|rrhh)\b",
                str(normalized or ""),
            )
        )
        if rrhh_match and domain in {"", "general"}:
            return "empleados"

        if any(token in normalized for token in ("ausent", "asistencia", "injustific")):
            return "ausentismo"
        if rrhh_match:
            return "empleados"
        if any(token in normalized for token in ("transporte", "ruta", "movilidad", "vehicul")):
            return "transport"
        return domain or "general"

    @staticmethod
    def _has_group_dimension_signal(normalized: str) -> bool:
        return bool(
            re.search(
                r"\b(supervisor(?:es)?|jefe(?:s)?|lider(?:es)?|area|areas|cargo|cargos|carpeta|carpetas)\b",
                str(normalized or ""),
            )
        )

    @staticmethod
    def _has_aggregate_signal(normalized: str) -> bool:
        text = str(normalized or "")
        if "concentra" in text or "concentran" in text:
            return True
        if "distribucion" in text or "participacion" in text:
            return True
        if QueryIntentResolver._has_group_dimension_signal(text) and any(
            token in text for token in ("mas", "top", "compar", "versus", "vs")
        ):
            return True
        return False
