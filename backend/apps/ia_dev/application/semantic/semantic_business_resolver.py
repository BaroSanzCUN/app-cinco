from __future__ import annotations

import re
from datetime import date
from typing import Any

from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    ResolvedQuerySpec,
    StructuredQueryIntent,
)
from apps.ia_dev.application.delegation.domain_registry import DomainRegistry
from apps.ia_dev.services.dictionary_tool_service import DictionaryToolService
from apps.ia_dev.services.period_service import resolve_period_from_text


class SemanticBusinessResolver:
    """
    Convierte intencion estructurada en especificacion operativa de negocio
    usando contexto semantico (YAML + catalogo DB + ai_dictionary).
    """

    DOMAIN_TO_DICTIONARY_CODE = {
        "ausentismo": "attendance",
        "attendance": "attendance",
        "empleados": "rrhh",
        "rrhh": "rrhh",
        "transporte": "transport",
        "transport": "transport",
    }

    def __init__(
        self,
        *,
        registry: DomainRegistry | None = None,
        dictionary_tool: DictionaryToolService | None = None,
    ):
        self.registry = registry or DomainRegistry()
        self.dictionary_tool = dictionary_tool or DictionaryToolService()

    def build_semantic_context(self, *, domain_code: str, include_dictionary: bool = True) -> dict[str, Any]:
        normalized_domain = self.registry.normalize_domain_code(domain_code)
        domain = self.registry.get_domain(normalized_domain)
        raw = dict((domain.raw_context if domain else {}) or {})

        tables = self._extract_tables(raw)
        columns = self._extract_columns(raw)
        relationships = self._extract_relationships(raw)
        capabilities = list(raw.get("capabilities") or [])
        flags = dict(raw.get("flags") or {})

        dictionary_context: dict[str, Any] = {}
        if include_dictionary:
            dictionary_domain = self.DOMAIN_TO_DICTIONARY_CODE.get(normalized_domain, normalized_domain or "general")
            try:
                dictionary_context = self.dictionary_tool.get_domain_context(dictionary_domain, limit=20)
            except Exception:
                dictionary_context = {}

        dictionary_fields = list(dictionary_context.get("fields") or [])
        dictionary_relations = list(dictionary_context.get("relations") or [])
        dictionary_synonyms = list(dictionary_context.get("synonyms") or [])
        dictionary_rules = list(dictionary_context.get("rules") or [])

        allowed_tables = self._collect_allowed_tables(tables=tables, dictionary_context=dictionary_context)
        allowed_columns = self._collect_allowed_columns(columns=columns, dictionary_fields=dictionary_fields)
        aliases = self._collect_aliases(columns=columns, dictionary_fields=dictionary_fields, dictionary_synonyms=dictionary_synonyms)

        return {
            "domain_code": normalized_domain,
            "domain_status": str(getattr(domain, "domain_status", raw.get("domain_status", "planned")) or "planned"),
            "maturity_level": str(getattr(domain, "maturity_level", raw.get("maturity_level", "initial")) or "initial"),
            "schema_confidence": float(getattr(domain, "schema_confidence", raw.get("schema_confidence", 0.0)) or 0.0),
            "main_entity": str(getattr(domain, "main_entity", raw.get("main_entity", "")) or ""),
            "business_goal": str(getattr(domain, "business_goal", raw.get("business_goal", "")) or ""),
            "tables": tables,
            "columns": columns,
            "relationships": relationships,
            "capabilities": capabilities,
            "flags": flags,
            "dictionary": {
                "fields": dictionary_fields,
                "relations": dictionary_relations,
                "rules": dictionary_rules,
                "synonyms": dictionary_synonyms,
            },
            "allowed_tables": allowed_tables,
            "allowed_columns": allowed_columns,
            "aliases": aliases,
            "supports_sql_assisted": bool(flags.get("sql_asistido_permitido")),
        }

    def resolve_query(
        self,
        *,
        message: str,
        intent: StructuredQueryIntent,
        base_classification: dict[str, Any],
    ) -> ResolvedQuerySpec:
        domain_code = self.registry.normalize_domain_code(intent.domain_code or base_classification.get("domain"))
        semantic_context = self.build_semantic_context(domain_code=domain_code, include_dictionary=True)
        normalized_filters = self._normalize_filters(
            message=message,
            domain_code=domain_code,
            intent=intent,
            semantic_context=semantic_context,
        )
        normalized_period = self._normalize_period(
            message=message,
            intent=intent,
        )
        mapped_columns = self._map_filter_columns(
            filters=normalized_filters,
            semantic_context=semantic_context,
        )
        warnings = self._build_warnings(
            domain_code=domain_code,
            intent=intent,
            normalized_filters=normalized_filters,
            normalized_period=normalized_period,
            semantic_context=semantic_context,
        )
        return ResolvedQuerySpec(
            intent=StructuredQueryIntent(
                raw_query=intent.raw_query,
                domain_code=domain_code,
                operation=intent.operation,
                template_id=intent.template_id,
                entity_type=intent.entity_type,
                entity_value=intent.entity_value,
                filters=dict(intent.filters or {}),
                period=dict(intent.period or {}),
                group_by=list(intent.group_by or []),
                metrics=list(intent.metrics or []),
                confidence=float(intent.confidence or 0.0),
                source=intent.source,
                warnings=list(intent.warnings or []),
            ),
            semantic_context=semantic_context,
            normalized_filters=normalized_filters,
            normalized_period=normalized_period,
            mapped_columns=mapped_columns,
            warnings=warnings,
        )

    @staticmethod
    def _extract_tables(raw: dict[str, Any]) -> list[dict[str, Any]]:
        values = raw.get("tables") or raw.get("tablas_asociadas") or []
        if not isinstance(values, list):
            return []
        tables: list[dict[str, Any]] = []
        for item in values:
            if isinstance(item, dict):
                schema_name = str(item.get("schema_name") or "").strip()
                table_name = str(item.get("table_name") or "").strip()
                table_fqn = str(item.get("table_fqn") or "").strip()
                if not table_fqn and table_name:
                    table_fqn = f"{schema_name}.{table_name}" if schema_name else table_name
                tables.append(
                    {
                        "schema_name": schema_name,
                        "table_name": table_name,
                        "table_fqn": table_fqn,
                        "nombre_tabla_logico": str(item.get("nombre_tabla_logico") or item.get("alias_negocio") or "").strip(),
                        "rol": str(item.get("rol") or item.get("rol_tabla") or "").strip(),
                        "es_principal": bool(item.get("es_principal")),
                    }
                )
            elif isinstance(item, str):
                clean = str(item).strip()
                schema_name, table_name = SemanticBusinessResolver._split_table_name(clean)
                tables.append(
                    {
                        "schema_name": schema_name or "",
                        "table_name": table_name,
                        "table_fqn": clean,
                        "nombre_tabla_logico": "",
                        "rol": "",
                        "es_principal": False,
                    }
                )
        return tables

    @staticmethod
    def _extract_columns(raw: dict[str, Any]) -> list[dict[str, Any]]:
        values = raw.get("columns") or raw.get("columnas_clave") or []
        if not isinstance(values, list):
            return []
        columns: list[dict[str, Any]] = []
        for item in values:
            if not isinstance(item, dict):
                continue
            columns.append(
                {
                    "table_name": str(item.get("table_name") or "").strip(),
                    "column_name": str(item.get("column_name") or "").strip(),
                    "nombre_columna_logico": str(item.get("nombre_columna_logico") or item.get("campo_logico") or "").strip(),
                    "descripcion": str(item.get("descripcion") or item.get("definicion_negocio") or "").strip(),
                    "es_filtro": bool(item.get("es_filtro")),
                    "es_group_by": bool(item.get("es_group_by")),
                    "es_metrica": bool(item.get("es_metrica")),
                    "es_clave": bool(item.get("es_clave")),
                }
            )
        return columns

    @staticmethod
    def _extract_relationships(raw: dict[str, Any]) -> list[dict[str, Any]]:
        values = raw.get("relationships") or raw.get("joins_conocidos") or []
        if not isinstance(values, list):
            return []
        relationships: list[dict[str, Any]] = []
        for item in values:
            if not isinstance(item, dict):
                continue
            relationships.append(
                {
                    "nombre_relacion": str(item.get("nombre_relacion") or "").strip(),
                    "condicion": str(item.get("condicion") or item.get("condicion_join_sql") or "").strip(),
                    "cardinalidad": str(item.get("cardinalidad") or "").strip(),
                }
            )
        return relationships

    @staticmethod
    def _collect_allowed_tables(*, tables: list[dict[str, Any]], dictionary_context: dict[str, Any]) -> list[str]:
        values: list[str] = []
        for item in tables:
            table_name = str(item.get("table_name") or "").strip().lower()
            table_fqn = str(item.get("table_fqn") or "").strip().lower()
            if table_name:
                values.append(table_name)
            if table_fqn:
                values.append(table_fqn)
        for row in list(dictionary_context.get("tables") or []):
            if not isinstance(row, dict):
                continue
            schema_name = str(row.get("schema_name") or "").strip().lower()
            table_name = str(row.get("table_name") or "").strip().lower()
            if table_name:
                values.append(table_name)
                values.append(f"{schema_name}.{table_name}" if schema_name else table_name)
        return sorted({item for item in values if item})

    @staticmethod
    def _collect_allowed_columns(*, columns: list[dict[str, Any]], dictionary_fields: list[dict[str, Any]]) -> list[str]:
        values: set[str] = set()
        for item in columns:
            col = str(item.get("column_name") or "").strip().lower()
            logical = str(item.get("nombre_columna_logico") or "").strip().lower()
            if col:
                values.add(col)
            if logical:
                values.add(logical)
        for row in dictionary_fields:
            if not isinstance(row, dict):
                continue
            col = str(row.get("column_name") or "").strip().lower()
            logical = str(row.get("campo_logico") or "").strip().lower()
            if col:
                values.add(col)
            if logical:
                values.add(logical)
        return sorted(values)

    @staticmethod
    def _collect_aliases(
        *,
        columns: list[dict[str, Any]],
        dictionary_fields: list[dict[str, Any]],
        dictionary_synonyms: list[dict[str, Any]],
    ) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for item in columns:
            logical = str(item.get("nombre_columna_logico") or "").strip().lower()
            physical = str(item.get("column_name") or "").strip().lower()
            if logical and physical:
                aliases[logical] = physical
        for row in dictionary_fields:
            if not isinstance(row, dict):
                continue
            logical = str(row.get("campo_logico") or "").strip().lower()
            physical = str(row.get("column_name") or "").strip().lower()
            if logical and physical:
                aliases[logical] = physical
        for row in dictionary_synonyms:
            if not isinstance(row, dict):
                continue
            term = str(row.get("termino") or "").strip().lower()
            synonym = str(row.get("sinonimo") or "").strip().lower()
            if term and synonym and term in aliases and synonym not in aliases:
                aliases[synonym] = aliases[term]
        return aliases

    def _normalize_filters(
        self,
        *,
        message: str,
        domain_code: str,
        intent: StructuredQueryIntent,
        semantic_context: dict[str, Any],
    ) -> dict[str, Any]:
        filters = dict(intent.filters or {})
        normalized_message = self._normalize_text(message)
        entity_value = self._normalize_identifier(intent.entity_value)
        if not entity_value:
            entity_value = self._extract_identifier_from_message(normalized_message)

        if entity_value and (intent.entity_type in {"empleado", "cedula", ""} or "empleado" in normalized_message):
            filters.setdefault("cedula", entity_value)

        if domain_code == "empleados":
            asks_active = (
                "activo" in normalized_message
                or "activos" in normalized_message
                or str(filters.get("estado") or "").strip().upper() == "ACTIVO"
            )
            asks_count = any(token in normalized_message for token in ("cantidad", "cuantos", "cuantas", "total", "numero"))
            if asks_active or asks_count:
                filters["estado"] = "ACTIVO"

        for key in ("supervisor", "area", "cargo", "carpeta"):
            value = self._extract_after_keyword(normalized_message, key)
            if value and key not in filters:
                filters[key] = value

        canonical_filters: dict[str, Any] = {}
        aliases = dict(semantic_context.get("aliases") or {})
        for key, value in filters.items():
            clean_key = str(key or "").strip().lower()
            if not clean_key:
                continue
            mapped = aliases.get(clean_key, clean_key)
            canonical_filters[mapped] = value
        return canonical_filters

    @staticmethod
    def _normalize_period(*, message: str, intent: StructuredQueryIntent) -> dict[str, Any]:
        period = dict(intent.period or {})
        if not period.get("start_date") or not period.get("end_date"):
            resolved = resolve_period_from_text(message)
            start = resolved.get("start")
            end = resolved.get("end")
            period = {
                "label": str(resolved.get("label") or ""),
                "start_date": start.isoformat() if hasattr(start, "isoformat") else None,
                "end_date": end.isoformat() if hasattr(end, "isoformat") else None,
            }
        return {
            "label": str(period.get("label") or ""),
            "start_date": str(period.get("start_date") or ""),
            "end_date": str(period.get("end_date") or ""),
        }

    @staticmethod
    def _map_filter_columns(*, filters: dict[str, Any], semantic_context: dict[str, Any]) -> dict[str, str]:
        aliases = dict(semantic_context.get("aliases") or {})
        mapped: dict[str, str] = {}
        for key in filters.keys():
            clean = str(key or "").strip().lower()
            if not clean:
                continue
            mapped[clean] = str(aliases.get(clean, clean))
        return mapped

    @staticmethod
    def _build_warnings(
        *,
        domain_code: str,
        intent: StructuredQueryIntent,
        normalized_filters: dict[str, Any],
        normalized_period: dict[str, Any],
        semantic_context: dict[str, Any],
    ) -> list[str]:
        warnings: list[str] = []
        if not domain_code:
            warnings.append("domain_not_resolved")
        if intent.operation in {"count", "aggregate", "trend", "detail"} and not semantic_context.get("tables"):
            warnings.append("semantic_tables_not_available")
        if intent.operation in {"count", "detail", "aggregate", "trend"} and not normalized_period.get("start_date"):
            warnings.append("period_not_resolved")
        if "cedula" in normalized_filters and not str(normalized_filters.get("cedula") or "").isdigit():
            warnings.append("cedula_filter_not_normalized")
        return warnings

    @staticmethod
    def _split_table_name(value: str) -> tuple[str | None, str]:
        clean = str(value or "").strip()
        if "." not in clean:
            return None, clean
        schema, table = clean.split(".", 1)
        return schema, table

    @staticmethod
    def _normalize_text(value: str) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _normalize_identifier(value: str | None) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    @staticmethod
    def _extract_identifier_from_message(message: str) -> str:
        match = re.search(r"\b\d{6,13}\b", str(message or ""))
        if not match:
            return ""
        return "".join(ch for ch in match.group(0) if ch.isdigit())

    @staticmethod
    def _extract_after_keyword(message: str, keyword: str) -> str:
        match = re.search(rf"\b{re.escape(keyword)}\s+([a-z0-9 ._-]{{2,80}})", message)
        if not match:
            return ""
        value = str(match.group(1) or "").strip(" .,-")
        for token in (" y ", " de ", " con ", " para ", " en "):
            if token in value:
                value = value.split(token, 1)[0].strip()
        return value

    @staticmethod
    def parse_iso_date(value: str | None) -> date | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except Exception:
            return None
