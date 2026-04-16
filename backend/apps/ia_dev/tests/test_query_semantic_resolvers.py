from __future__ import annotations

import os
from dataclasses import dataclass
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    StructuredQueryIntent,
)
from apps.ia_dev.application.semantic.column_semantic_resolver import (
    ColumnSemanticResolver,
)
from apps.ia_dev.application.semantic.relation_semantic_resolver import (
    RelationSemanticResolver,
)
from apps.ia_dev.application.semantic.rule_semantic_resolver import RuleSemanticResolver
from apps.ia_dev.application.semantic.semantic_business_resolver import (
    SemanticBusinessResolver,
)
from apps.ia_dev.application.semantic.synonym_semantic_resolver import (
    SynonymSemanticResolver,
)


@dataclass
class _FakeDomain:
    raw_context: dict
    domain_status: str = "active"
    maturity_level: str = "mature"
    schema_confidence: float = 0.95
    main_entity: str = "empleado"
    business_goal: str = "analytics"


class _FakeRegistry:
    def __init__(self, domain: _FakeDomain):
        self._domain = domain

    @staticmethod
    def normalize_domain_code(value: str | None) -> str:
        return str(value or "").strip().lower() or "empleados"

    def get_domain(self, domain_code: str | None):
        return self._domain


class _FakeDictionaryTool:
    @staticmethod
    def get_domain_context(domain: str, *, limit: int = 20) -> dict:
        return {
            "domain": {"id": 1, "code": "USUARIOS", "matched": True},
            "tables": [
                {
                    "id": 1,
                    "schema_name": "cincosas_cincosas",
                    "table_name": "cinco_base_de_personal",
                }
            ],
            "fields": [
                {
                    "table_name": "cinco_base_de_personal",
                    "campo_logico": "estado_usuario",
                    "column_name": "estado",
                    "valores_permitidos": "ACTIVO,INACTIVO",
                    "es_filtro": True,
                },
                {
                    "table_name": "cinco_base_de_personal",
                    "campo_logico": "supervisor",
                    "column_name": "supervisor",
                    "es_group_by": True,
                },
                {
                    "table_name": "cinco_base_de_personal",
                    "campo_logico": "area",
                    "column_name": "area",
                    "es_group_by": True,
                },
                {
                    "table_name": "cinco_base_de_personal",
                    "campo_logico": "cedula",
                    "column_name": "cedula",
                    "is_identifier": True,
                    "es_filtro": True,
                },
            ],
            "field_profiles": [],
            "rules": [{"resultado_funcional": "empleado = cedula"}],
            "relations": [
                {
                    "nombre_relacion": "empleado_supervisor",
                    "join_sql": "cinco_base_de_personal.supervisor = cinco_base_de_personal.cedula",
                    "cardinalidad": "many_to_one",
                }
            ],
            "synonyms": [
                {"termino": "supervisor", "sinonimo": "jefe"},
                {"termino": "supervisor", "sinonimo": "lider"},
                {"termino": "activo", "sinonimo": "habilitado"},
                {"termino": "activo", "sinonimo": "habilitados"},
            ],
        }


class QuerySemanticResolversTests(SimpleTestCase):
    def test_synonym_semantic_resolver_canonicalize(self):
        resolver = SynonymSemanticResolver()
        index = resolver.build_index(
            dictionary_synonyms=[{"termino": "supervisor", "sinonimo": "jefe"}],
            dictionary_fields=[],
            runtime_columns=[],
        )
        self.assertEqual(resolver.canonicalize(term="jefe", synonym_index=index), "supervisor")

    def test_column_semantic_resolver_normalizes_status_filter(self):
        resolver = ColumnSemanticResolver()
        profiles = resolver.build_column_profiles(
            runtime_columns=[],
            dictionary_fields=[
                {
                    "table_name": "cinco_base_de_personal",
                    "campo_logico": "estado",
                    "column_name": "estado",
                    "valores_permitidos": "ACTIVO,INACTIVO",
                    "es_filtro": True,
                }
            ],
        )
        semantic_context = {"column_profiles": profiles}
        normalized, _ = resolver.resolve_filters(
            filters={"estado": "inactivos"},
            semantic_context=semantic_context,
            canonicalize_term=lambda term: str(term or "").lower(),
            normalize_status_value=lambda raw, allowed: RuleSemanticResolver().normalize_status_value(
                raw_value=raw,
                allowed_values=allowed,
            ),
        )
        self.assertEqual(str(normalized.get("estado") or ""), "INACTIVO")

    def test_rule_semantic_resolver_extracts_identifier(self):
        resolver = RuleSemanticResolver()
        value = resolver.infer_identifier_from_message(
            message="Ausentismos del empleado 1055837370",
            domain_code="ausentismo",
        )
        self.assertEqual(value.get("cedula"), "1055837370")

    def test_semantic_business_resolver_resolves_filters_group_by_and_relations(self):
        fake_domain = _FakeDomain(
            raw_context={
                "tables": [
                    {
                        "schema_name": "cincosas_cincosas",
                        "table_name": "cinco_base_de_personal",
                        "table_fqn": "cincosas_cincosas.cinco_base_de_personal",
                        "rol": "dimension",
                        "es_principal": True,
                    }
                ],
                "columns": [
                    {"table_name": "cinco_base_de_personal", "column_name": "cedula", "nombre_columna_logico": "cedula"},
                    {"table_name": "cinco_base_de_personal", "column_name": "estado", "nombre_columna_logico": "estado"},
                    {"table_name": "cinco_base_de_personal", "column_name": "supervisor", "nombre_columna_logico": "supervisor"},
                    {"table_name": "cinco_base_de_personal", "column_name": "area", "nombre_columna_logico": "area"},
                ],
                "relationships": [
                    {
                        "nombre_relacion": "empleado_supervisor",
                        "condicion_join_sql": "cinco_base_de_personal.supervisor = cinco_base_de_personal.cedula",
                        "cardinalidad": "many_to_one",
                    }
                ],
                "flags": {"sql_asistido_permitido": False},
            }
        )
        resolver = SemanticBusinessResolver(
            registry=_FakeRegistry(fake_domain),
            dictionary_tool=_FakeDictionaryTool(),
        )
        intent = StructuredQueryIntent(
            raw_query="Cantidad empleados inactivos por jefe del empleado 1055837370",
            domain_code="empleados",
            operation="count",
            template_id="count_entities_by_status",
            filters={"estado": "inactivos"},
            group_by=["jefe"],
            metrics=["count"],
            confidence=0.9,
        )
        resolved = resolver.resolve_query(
            message=intent.raw_query,
            intent=intent,
            base_classification={"domain": "empleados"},
        )
        self.assertEqual(str(resolved.normalized_filters.get("estado") or ""), "INACTIVO")
        self.assertEqual(str(resolved.normalized_filters.get("cedula") or ""), "1055837370")
        self.assertIn("supervisor", list(resolved.intent.group_by or []))
        relation_payload = dict((resolved.semantic_context or {}).get("resolved_semantic") or {})
        self.assertTrue(list(relation_payload.get("relations") or []))

    def test_semantic_business_resolver_inferrs_group_by_area_from_plural_question(self):
        fake_domain = _FakeDomain(
            raw_context={
                "tables": [
                    {
                        "schema_name": "cincosas_cincosas",
                        "table_name": "cinco_base_de_personal",
                        "table_fqn": "cincosas_cincosas.cinco_base_de_personal",
                        "rol": "dimension",
                        "es_principal": True,
                    }
                ],
                "columns": [
                    {"table_name": "cinco_base_de_personal", "column_name": "area", "nombre_columna_logico": "area"},
                ],
                "relationships": [],
                "flags": {"sql_asistido_permitido": False},
            }
        )
        resolver = SemanticBusinessResolver(
            registry=_FakeRegistry(fake_domain),
            dictionary_tool=_FakeDictionaryTool(),
        )
        intent = StructuredQueryIntent(
            raw_query="¿Qué áreas concentran más ausentismos en rolling 90 días?",
            domain_code="ausentismo",
            operation="aggregate",
            template_id="aggregate_by_group_and_period",
            filters={},
            group_by=[],
            metrics=["count"],
            confidence=0.9,
        )
        resolved = resolver.resolve_query(
            message=intent.raw_query,
            intent=intent,
            base_classification={"domain": "ausentismo"},
        )
        self.assertIn("area", list(resolved.intent.group_by or []))

    def test_semantic_business_resolver_resolves_habilitados_status_from_dictionary(self):
        fake_domain = _FakeDomain(
            raw_context={
                "tables": [
                    {
                        "schema_name": "cincosas_cincosas",
                        "table_name": "cinco_base_de_personal",
                        "table_fqn": "cincosas_cincosas.cinco_base_de_personal",
                        "rol": "dimension",
                        "es_principal": True,
                    }
                ],
                "columns": [
                    {"table_name": "cinco_base_de_personal", "column_name": "estado", "nombre_columna_logico": "estado_usuario"},
                ],
                "relationships": [],
                "flags": {"sql_asistido_permitido": False},
            }
        )
        resolver = SemanticBusinessResolver(
            registry=_FakeRegistry(fake_domain),
            dictionary_tool=_FakeDictionaryTool(),
        )
        intent = StructuredQueryIntent(
            raw_query="¿Cuántos colaboradores habilitados tenemos hoy?",
            domain_code="empleados",
            operation="count",
            template_id="count_records_by_period",
            filters={},
            group_by=[],
            metrics=["count"],
            confidence=0.9,
        )
        resolved = resolver.resolve_query(
            message=intent.raw_query,
            intent=intent,
            base_classification={"domain": "empleados"},
        )
        self.assertEqual(str(resolved.normalized_filters.get("estado") or ""), "ACTIVO")
        self.assertEqual(str(resolved.intent.template_id or ""), "count_entities_by_status")

    def test_relation_semantic_resolver_builds_relation_profiles(self):
        resolver = RelationSemanticResolver()
        profiles = resolver.build_relation_profiles(
            runtime_relationships=[],
            dictionary_relations=[
                {
                    "nombre_relacion": "ausentismo_empleado",
                    "join_sql": "gestionh_ausentismo.cedula = cinco_base_de_personal.cedula",
                    "cardinalidad": "many_to_one",
                }
            ],
        )
        self.assertEqual(len(profiles), 1)
        self.assertEqual(str(profiles[0].get("relation_name") or ""), "ausentismo_empleado")

    def test_semantic_business_resolver_rrhh_synonym_seed_flag_controls_bootstrap(self):
        fake_domain = _FakeDomain(raw_context={"tables": [], "columns": [], "relationships": [], "flags": {}})
        dictionary_tool = Mock()
        dictionary_tool.get_domain_context.return_value = {
            "fields": [],
            "relations": [],
            "rules": [],
            "synonyms": [],
            "field_profiles": [],
            "tables": [],
        }
        dictionary_tool.ensure_rrhh_status_synonyms_seed.return_value = {
            "ok": True,
            "status": "applied",
            "inserted": 2,
            "skipped": 6,
            "errors": [],
        }
        resolver = SemanticBusinessResolver(
            registry=_FakeRegistry(fake_domain),
            dictionary_tool=dictionary_tool,
        )

        with patch.dict(
            os.environ,
            {"IA_DEV_QUERY_INTELLIGENCE_RRHH_SYNONYM_SEED_ENABLED": "0"},
            clear=False,
        ):
            context = resolver.build_semantic_context(domain_code="empleados", include_dictionary=True)
        self.assertEqual(str((context.get("dictionary_seed") or {}).get("status") or ""), "skipped")
        dictionary_tool.ensure_rrhh_status_synonyms_seed.assert_not_called()

        with patch.dict(
            os.environ,
            {"IA_DEV_QUERY_INTELLIGENCE_RRHH_SYNONYM_SEED_ENABLED": "1"},
            clear=False,
        ):
            context = resolver.build_semantic_context(domain_code="empleados", include_dictionary=True)
        self.assertEqual(str((context.get("dictionary_seed") or {}).get("status") or ""), "applied")
        dictionary_tool.ensure_rrhh_status_synonyms_seed.assert_called()
