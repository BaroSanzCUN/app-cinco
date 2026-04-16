from __future__ import annotations

import os
import re
import unicodedata
from datetime import date
from typing import Any

from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    ResolvedQuerySpec,
    StructuredQueryIntent,
)
from apps.ia_dev.application.delegation.domain_registry import DomainRegistry
from apps.ia_dev.application.semantic.column_semantic_resolver import ColumnSemanticResolver
from apps.ia_dev.application.semantic.relation_semantic_resolver import RelationSemanticResolver
from apps.ia_dev.application.semantic.rule_semantic_resolver import RuleSemanticResolver
from apps.ia_dev.application.semantic.synonym_semantic_resolver import SynonymSemanticResolver
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
        column_resolver: ColumnSemanticResolver | None = None,
        relation_resolver: RelationSemanticResolver | None = None,
        rule_resolver: RuleSemanticResolver | None = None,
        synonym_resolver: SynonymSemanticResolver | None = None,
    ):
        self.registry = registry or DomainRegistry()
        self.dictionary_tool = dictionary_tool or DictionaryToolService()
        self.column_resolver = column_resolver or ColumnSemanticResolver()
        self.relation_resolver = relation_resolver or RelationSemanticResolver()
        self.rule_resolver = rule_resolver or RuleSemanticResolver()
        self.synonym_resolver = synonym_resolver or SynonymSemanticResolver()

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
        dictionary_seed: dict[str, Any] = {
            "enabled": False,
            "status": "skipped",
            "inserted": 0,
            "skipped": 0,
            "errors": [],
        }
        if include_dictionary:
            dictionary_domain = self.DOMAIN_TO_DICTIONARY_CODE.get(normalized_domain, normalized_domain or "general")
            if dictionary_domain == "rrhh":
                dictionary_seed = self._maybe_seed_rrhh_status_synonyms()
            try:
                dictionary_context = self.dictionary_tool.get_domain_context(dictionary_domain, limit=20)
            except Exception:
                dictionary_context = {}

        dictionary_fields = list(dictionary_context.get("fields") or [])
        dictionary_relations = list(dictionary_context.get("relations") or [])
        dictionary_synonyms = list(dictionary_context.get("synonyms") or [])
        dictionary_rules = list(dictionary_context.get("rules") or [])
        dictionary_field_profiles = list(dictionary_context.get("field_profiles") or [])

        column_profiles = self.column_resolver.build_column_profiles(
            runtime_columns=columns,
            dictionary_fields=dictionary_fields,
        )
        if dictionary_field_profiles:
            # Prefer perfiles persistidos cuando existan.
            column_profiles = self.column_resolver.build_column_profiles(
                runtime_columns=columns,
                dictionary_fields=dictionary_field_profiles + dictionary_fields,
            )

        relation_profiles = self.relation_resolver.build_relation_profiles(
            runtime_relationships=relationships,
            dictionary_relations=dictionary_relations,
        )

        synonym_index = self.synonym_resolver.build_index(
            dictionary_synonyms=dictionary_synonyms,
            dictionary_fields=dictionary_fields,
            runtime_columns=columns,
        )

        allowed_tables = self._collect_allowed_tables(tables=tables, dictionary_context=dictionary_context)
        allowed_columns = self._collect_allowed_columns(columns=columns, dictionary_fields=dictionary_fields)
        aliases = self._collect_aliases(columns=columns, dictionary_fields=dictionary_fields, dictionary_synonyms=dictionary_synonyms)
        aliases = {**synonym_index, **aliases}

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
                "field_profiles": dictionary_field_profiles,
            },
            "dictionary_meta": {
                "schema": str(dictionary_context.get("schema") or ""),
                "dictionary_table": str(dictionary_context.get("dictionary_table") or ""),
                "profile_table_name": str(dictionary_context.get("profile_table_name") or ""),
                "domain": dict(dictionary_context.get("domain") or {}),
            },
            "column_profiles": column_profiles,
            "relation_profiles": relation_profiles,
            "synonym_index": synonym_index,
            "allowed_tables": allowed_tables,
            "allowed_columns": allowed_columns,
            "aliases": aliases,
            "supports_sql_assisted": bool(flags.get("sql_asistido_permitido")),
            "dictionary_seed": dictionary_seed,
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
        synonym_index = dict(semantic_context.get("synonym_index") or {})

        def canonicalize_term(value: str | None) -> str:
            return self.synonym_resolver.canonicalize(
                term=value,
                synonym_index=synonym_index,
            )

        dictionary_rules = list((semantic_context.get("dictionary") or {}).get("rules") or [])
        rule_filters = self.rule_resolver.apply_rule_overrides(
            message=message,
            domain_code=domain_code,
            filters=dict(intent.filters or {}),
            dictionary_rules=dictionary_rules,
        )
        identifier_filter = self.column_resolver.resolve_identifier_filter(
            message=message,
            semantic_context=semantic_context,
        )
        if identifier_filter:
            identifier_key, identifier_value = identifier_filter
            rule_filters.setdefault(identifier_key, identifier_value)

        normalized_filters, filter_resolutions = self.column_resolver.resolve_filters(
            filters=rule_filters,
            semantic_context=semantic_context,
            canonicalize_term=canonicalize_term,
            normalize_status_value=self.rule_resolver.normalize_status_value,
        )
        status_resolution = self._resolve_status_from_dictionary(
            message=message,
            semantic_context=semantic_context,
            normalized_filters=normalized_filters,
            canonicalize_term=canonicalize_term,
        )
        if status_resolution:
            status_key = str(status_resolution.get("status_key") or "estado").strip().lower() or "estado"
            status_value = str(status_resolution.get("status_value") or "").strip().upper()
            if status_value:
                normalized_filters[status_key] = status_value
                normalized_filters.setdefault("estado", status_value)
        status_value_after_normalization = self._extract_status_value(normalized_filters)
        if status_value_after_normalization and "estado" not in normalized_filters:
            normalized_filters["estado"] = status_value_after_normalization
        resolved_group_by, group_resolutions = self.column_resolver.resolve_group_by(
            requested_group_by=list(intent.group_by or []),
            message=message,
            semantic_context=semantic_context,
            canonicalize_term=canonicalize_term,
        )
        resolved_metrics, metric_resolutions = self.column_resolver.resolve_metrics(
            requested_metrics=list(intent.metrics or []),
            operation=intent.operation,
            message=message,
            semantic_context=semantic_context,
            canonicalize_term=canonicalize_term,
        )
        normalized_period = self._normalize_period(
            message=message,
            intent=intent,
        )
        mapped_columns = self._map_filter_columns(
            filters=normalized_filters,
            semantic_context=semantic_context,
        )
        relation_resolutions = self.relation_resolver.resolve_required_relations(
            semantic_context=semantic_context,
            requested_terms=[
                *list(normalized_filters.keys()),
                *list(resolved_group_by),
            ],
        )
        status_value = self._extract_status_value(normalized_filters)
        resolved_template_id = str(intent.template_id or "").strip().lower()
        if domain_code in {"empleados", "rrhh"} and str(intent.operation or "").strip().lower() == "count" and status_value:
            resolved_template_id = "count_entities_by_status"

        resolution_payload = {
            "filters": [item.as_dict() for item in filter_resolutions],
            "group_by": [item.as_dict() for item in group_resolutions],
            "metrics": [item.as_dict() for item in metric_resolutions],
            "relations": [item.as_dict() for item in relation_resolutions],
        }
        semantic_context["resolved_semantic"] = resolution_payload
        if status_resolution:
            semantic_events = list(semantic_context.get("semantic_events") or [])
            semantic_events.append(
                {
                    "event_type": "semantic_status_resolved_from_dictionary",
                    "status_value": str(status_resolution.get("status_value") or ""),
                    "status_key": str(status_resolution.get("status_key") or "estado"),
                    "matched_token": str(status_resolution.get("matched_token") or ""),
                    "allowed_values": list(status_resolution.get("allowed_values") or []),
                }
            )
            semantic_context["semantic_events"] = semantic_events

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
                template_id=resolved_template_id or str(intent.template_id or ""),
                entity_type=intent.entity_type,
                entity_value=intent.entity_value,
                filters=dict(normalized_filters or {}),
                period=dict(intent.period or {}),
                group_by=list(resolved_group_by or []),
                metrics=list(resolved_metrics or []),
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
        synonym_index = dict(semantic_context.get("synonym_index") or {})
        filters = self.rule_resolver.apply_rule_overrides(
            message=message,
            domain_code=domain_code,
            filters=dict(intent.filters or {}),
            dictionary_rules=list((semantic_context.get("dictionary") or {}).get("rules") or []),
        )
        resolved, _ = self.column_resolver.resolve_filters(
            filters=filters,
            semantic_context=semantic_context,
            canonicalize_term=lambda term: self.synonym_resolver.canonicalize(
                term=term,
                synonym_index=synonym_index,
            ),
            normalize_status_value=self.rule_resolver.normalize_status_value,
        )
        return resolved

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
        lowered = str(value or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

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

    @staticmethod
    def _extract_status_value(filters: dict[str, Any]) -> str:
        for key in ("estado", "estado_usuario", "estado_empleado"):
            value = str((filters or {}).get(key) or "").strip().upper()
            if value in {"ACTIVO", "INACTIVO"}:
                return value
        return ""

    def _resolve_status_from_dictionary(
        self,
        *,
        message: str,
        semantic_context: dict[str, Any],
        normalized_filters: dict[str, Any],
        canonicalize_term,
    ) -> dict[str, Any]:
        if self._extract_status_value(normalized_filters):
            return {}
        status_profile = self._find_status_profile(semantic_context=semantic_context)
        if not status_profile:
            return {}

        status_key = str(status_profile.get("logical_name") or status_profile.get("column_name") or "estado").strip().lower()
        allowed_values = list(status_profile.get("allowed_values") or [])
        if not allowed_values:
            return {}
        allowed_set = {str(item or "").strip().upper() for item in allowed_values if str(item or "").strip()}
        if not allowed_set:
            return {}

        synonym_index = dict(semantic_context.get("synonym_index") or {})
        canonical_tokens = self.synonym_resolver.canonicalize_tokens_from_message(
            message=message,
            synonym_index=synonym_index,
        )
        raw_tokens = re.findall(r"[a-z0-9_]{2,}", self._normalize_text(message))
        tokens = list(dict.fromkeys([*canonical_tokens, *raw_tokens]))
        for token in tokens:
            mapped = str(canonicalize_term(token) or token).strip()
            normalized_value = self.rule_resolver.normalize_status_value(
                raw_value=mapped,
                allowed_values=allowed_values,
            )
            if normalized_value in allowed_set:
                return {
                    "status_key": status_key,
                    "status_value": normalized_value,
                    "matched_token": token,
                    "allowed_values": sorted(allowed_set),
                }
        return {}

    def _find_status_profile(self, *, semantic_context: dict[str, Any]) -> dict[str, Any]:
        profiles = list(semantic_context.get("column_profiles") or [])
        for profile in profiles:
            if not isinstance(profile, dict):
                continue
            logical_name = str(profile.get("logical_name") or "").strip().lower()
            column_name = str(profile.get("column_name") or "").strip().lower()
            allowed_values = [str(item or "").strip().upper() for item in list(profile.get("allowed_values") or []) if str(item or "").strip()]
            supports_filter = bool(profile.get("supports_filter"))
            if not supports_filter or not allowed_values:
                continue
            if logical_name in {"estado", "estado_usuario", "estado_empleado"} or column_name == "estado":
                return {
                    **profile,
                    "allowed_values": allowed_values,
                    "logical_name": logical_name or column_name or "estado",
                }
        return {}

    def _maybe_seed_rrhh_status_synonyms(self) -> dict[str, Any]:
        enabled = str(
            os.getenv("IA_DEV_QUERY_INTELLIGENCE_RRHH_SYNONYM_SEED_ENABLED", "0") or "0"
        ).strip().lower() in {"1", "true", "yes", "on"}
        if not enabled:
            return {
                "enabled": False,
                "status": "skipped",
                "inserted": 0,
                "skipped": 0,
                "errors": [],
            }
        result = self.dictionary_tool.ensure_rrhh_status_synonyms_seed()
        payload = dict(result or {})
        payload["enabled"] = True
        payload.setdefault("status", "skipped")
        payload.setdefault("inserted", 0)
        payload.setdefault("skipped", 0)
        payload.setdefault("errors", [])
        return payload
