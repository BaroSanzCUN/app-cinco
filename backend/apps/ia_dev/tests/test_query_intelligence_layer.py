from __future__ import annotations

import os
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    ResolvedQuerySpec,
    StructuredQueryIntent,
)
from apps.ia_dev.application.policies.query_execution_policy import QueryExecutionPolicy
from apps.ia_dev.application.semantic.query_execution_planner import QueryExecutionPlanner
from apps.ia_dev.application.semantic.query_intent_resolver import QueryIntentResolver
from apps.ia_dev.application.semantic.result_satisfaction_validator import (
    ResultSatisfactionValidator,
)


class QueryIntelligenceLayerTests(SimpleTestCase):
    def test_query_intent_resolver_rules_are_accent_insensitive_for_rrhh_count(self):
        resolver = QueryIntentResolver()
        with patch.dict(os.environ, {"IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED": "0"}, clear=False):
            intent = resolver.resolve(
                message="¿Cuántos colaboradores habilitados tenemos hoy?",
                base_classification={
                    "domain": "general",
                    "intent": "general_question",
                    "needs_database": False,
                },
                semantic_context={},
            )
        self.assertEqual(intent.domain_code, "empleados")
        self.assertEqual(intent.operation, "count")

    def test_query_intent_resolver_rules_for_empleados_activos(self):
        resolver = QueryIntentResolver()
        with patch.dict(os.environ, {"IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED": "0"}, clear=False):
            intent = resolver.resolve(
                message="Cantidad empleados activos",
                base_classification={
                    "domain": "empleados",
                    "intent": "empleados_query",
                    "needs_database": True,
                },
                semantic_context={},
            )
        self.assertEqual(intent.domain_code, "empleados")
        self.assertEqual(intent.operation, "count")
        self.assertEqual(intent.template_id, "count_entities_by_status")
        # El estado se resuelve en la capa semantica (dd_campos/dd_sinonimos), no en intent resolver.
        self.assertEqual(str(intent.filters.get("estado") or ""), "")

    def test_query_intent_resolver_detects_group_by_area_and_rolling_period_from_concentration_question(self):
        resolver = QueryIntentResolver()
        with patch.dict(os.environ, {"IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED": "0"}, clear=False):
            intent = resolver.resolve(
                message="¿Qué áreas concentran más ausentismos en rolling 90 días y qué causas probables sugieres?",
                base_classification={
                    "domain": "attendance",
                    "intent": "attendance_query",
                    "needs_database": True,
                },
                semantic_context={},
            )
        self.assertEqual(intent.domain_code, "attendance")
        self.assertEqual(intent.template_id, "aggregate_by_group_and_period")
        self.assertIn("area", list(intent.group_by or []))
        self.assertEqual(str((intent.period or {}).get("label") or ""), "rolling_90_dias")

    def test_query_execution_planner_selects_capability_for_empleados_count_active(self):
        planner = QueryExecutionPlanner()
        intent = StructuredQueryIntent(
            raw_query="Cantidad empleados activos",
            domain_code="empleados",
            operation="count",
            template_id="count_entities_by_status",
            filters={"estado": "ACTIVO"},
            period={},
            group_by=[],
            metrics=["count"],
            confidence=0.9,
            source="rules",
        )
        resolved_query = ResolvedQuerySpec(
            intent=intent,
            semantic_context={
                "domain_status": "active",
                "supports_sql_assisted": False,
                "tables": [{"table_fqn": "bd_c3nc4s1s.cinco_base_de_personal", "table_name": "cinco_base_de_personal"}],
                "allowed_tables": ["cinco_base_de_personal", "bd_c3nc4s1s.cinco_base_de_personal"],
                "allowed_columns": ["estado", "cedula"],
            },
            normalized_filters={"estado": "ACTIVO"},
            normalized_period={},
            mapped_columns={"estado": "estado"},
        )
        with patch.dict(
            os.environ,
            {
                "IA_DEV_CAP_EMPLEADOS_ENABLED": "1",
                "IA_DEV_CAP_EMPLEADOS_COUNT_ENABLED": "1",
            },
            clear=False,
        ):
            run_context = RunContext.create(message="Cantidad empleados activos")
            plan = planner.plan(
                run_context=run_context,
                resolved_query=resolved_query,
            )
        self.assertEqual(plan.strategy, "capability")
        self.assertEqual(plan.capability_id, "empleados.count.active.v1")

    def test_query_execution_planner_selects_rrhh_capability_even_with_generic_template(self):
        planner = QueryExecutionPlanner()
        intent = StructuredQueryIntent(
            raw_query="¿Cuántos colaboradores habilitados tenemos hoy?",
            domain_code="empleados",
            operation="count",
            template_id="count_records_by_period",
            filters={"estado_usuario": "ACTIVO"},
            period={},
            group_by=[],
            metrics=["count"],
            confidence=0.9,
            source="rules",
        )
        resolved_query = ResolvedQuerySpec(
            intent=intent,
            semantic_context={
                "domain_status": "active",
                "supports_sql_assisted": False,
                "tables": [{"table_fqn": "bd_c3nc4s1s.cinco_base_de_personal", "table_name": "cinco_base_de_personal"}],
                "allowed_tables": ["cinco_base_de_personal", "bd_c3nc4s1s.cinco_base_de_personal"],
                "allowed_columns": ["estado", "cedula"],
            },
            normalized_filters={"estado_usuario": "ACTIVO"},
            normalized_period={"label": "hoy", "start_date": "2026-04-16", "end_date": "2026-04-16"},
            mapped_columns={"estado_usuario": "estado"},
        )
        with patch.dict(
            os.environ,
            {
                "IA_DEV_CAP_EMPLEADOS_ENABLED": "1",
                "IA_DEV_CAP_EMPLEADOS_COUNT_ENABLED": "1",
            },
            clear=False,
        ):
            run_context = RunContext.create(message="¿Cuántos colaboradores habilitados tenemos hoy?")
            plan = planner.plan(
                run_context=run_context,
                resolved_query=resolved_query,
            )
        self.assertEqual(plan.strategy, "capability")
        self.assertEqual(plan.capability_id, "empleados.count.active.v1")

    def test_query_execution_policy_rejects_unsafe_sql(self):
        policy = QueryExecutionPolicy()
        decision = policy.validate_sql_query(
            query="UPDATE tabla SET a = 1 LIMIT 1",
            allowed_tables=["tabla"],
            allowed_columns=["a"],
            max_limit=100,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "sql_must_start_with_select")

    def test_result_satisfaction_validator_detects_cedula_mismatch(self):
        validator = ResultSatisfactionValidator()
        response = {
            "reply": "Detalle de ausentismos del periodo 2025-04-14 al 2026-04-13",
            "data": {
                "kpis": {},
                "table": {
                    "columns": ["cedula"],
                    "rows": [{"cedula": "1000087030"}, {"cedula": "1011510709"}],
                    "rowcount": 2,
                },
            },
        }
        validation = validator.validate(
            message="Ausentismos del ultimo ano del empleado 1055837370",
            response=response,
            resolved_query=None,
        )
        self.assertFalse(validation.satisfied)
        self.assertEqual(validation.reason, "entity_filter_not_applied_for_cedula")

    def test_result_satisfaction_validator_detects_group_count_not_aggregated(self):
        validator = ResultSatisfactionValidator()
        response = {
            "reply": "Detalle de ausentismos del periodo 2026-03-30 al 2026-04-13",
            "data": {
                "kpis": {"total_ausentismos": 150},
                "table": {
                    "columns": ["cedula", "fecha_ausentismo", "supervisor"],
                    "rows": [
                        {"cedula": "1000087030", "fecha_ausentismo": "2026-04-13", "supervisor": "A"},
                        {"cedula": "1011510709", "fecha_ausentismo": "2026-04-13", "supervisor": "B"},
                    ],
                    "rowcount": 2,
                },
            },
        }
        validation = validator.validate(
            message="Cantidad de ausentismos por supervisor los ultimos 15 dias",
            response=response,
            resolved_query=None,
        )
        self.assertFalse(validation.satisfied)
        self.assertEqual(validation.reason, "group_count_requested_but_result_is_not_aggregated")
