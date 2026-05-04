from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    QueryExecutionPlan,
    ResolvedQuerySpec,
    StructuredQueryIntent,
)
from apps.ia_dev.application.orchestration.chat_application_service import (
    ChatApplicationService,
)
from apps.ia_dev.application.policies.query_execution_policy import QueryExecutionPolicy
from apps.ia_dev.application.semantic.query_execution_planner import QueryExecutionPlanner
from apps.ia_dev.application.semantic.query_intent_resolver import QueryIntentResolver
from apps.ia_dev.services.intent_service import IntentClassifierService
from apps.ia_dev.services.runtime_governance_service import RuntimeGovernanceService


def _pilot_context() -> dict:
    return {
        "tables": [
            {"schema_name": "cincosas_cincosas", "table_name": "gestionh_ausentismo"},
            {"schema_name": "cincosas_cincosas", "table_name": "cinco_base_de_personal"},
        ],
        "column_profiles": [
            {"table_name": "gestionh_ausentismo", "logical_name": "fecha_ausentismo", "column_name": "fecha_edit"},
            {"table_name": "gestionh_ausentismo", "logical_name": "cedula", "column_name": "cedula"},
            {"table_name": "cinco_base_de_personal", "logical_name": "cedula", "column_name": "cedula"},
            {"table_name": "cinco_base_de_personal", "logical_name": "area", "column_name": "area"},
            {"table_name": "cinco_base_de_personal", "logical_name": "cargo", "column_name": "cargo"},
            {"table_name": "cinco_base_de_personal", "logical_name": "sede", "column_name": "zona_nodo"},
        ],
        "allowed_tables": [
            "cincosas_cincosas.gestionh_ausentismo",
            "cincosas_cincosas.cinco_base_de_personal",
        ],
        "allowed_columns": ["fecha_edit", "cedula", "area", "cargo", "zona_nodo"],
        "dictionary": {
            "relations": [
                {
                    "nombre_relacion": "ausentismo_empleado",
                    "join_sql": "gestionh_ausentismo.cedula = cinco_base_de_personal.cedula",
                }
            ]
        },
        "source_of_truth": {
            "pilot_sql_assisted_enabled": True,
            "used_dictionary": True,
            "used_yaml": True,
        },
        "query_hints": {
            "candidate_group_dimensions": ["area", "cargo", "sede"],
        },
        "supports_sql_assisted": True,
        "domain_status": "partial",
    }


def _employee_birthday_context() -> dict:
    return {
        "tables": [
            {"schema_name": "cincosas_cincosas", "table_name": "cinco_base_de_personal", "table_fqn": "cincosas_cincosas.cinco_base_de_personal"},
        ],
        "column_profiles": [
            {"table_name": "cinco_base_de_personal", "logical_name": "fecha_nacimiento", "column_name": "fnacimiento", "supports_filter": True, "supports_group_by": True, "is_date": True},
            {"table_name": "cinco_base_de_personal", "logical_name": "cedula", "column_name": "cedula", "is_identifier": True},
            {"table_name": "cinco_base_de_personal", "logical_name": "estado_empleado", "column_name": "estado", "supports_filter": True, "allowed_values": ["ACTIVO", "INACTIVO"]},
            {"table_name": "cinco_base_de_personal", "logical_name": "area", "column_name": "area", "supports_group_by": True, "supports_dimension": True},
            {"table_name": "cinco_base_de_personal", "logical_name": "cargo", "column_name": "cargo", "supports_group_by": True, "supports_dimension": True},
        ],
        "allowed_tables": ["cincosas_cincosas.cinco_base_de_personal", "cinco_base_de_personal"],
        "allowed_columns": ["fnacimiento", "cedula", "estado", "area", "cargo"],
        "dictionary": {"relations": []},
        "source_of_truth": {"pilot_sql_assisted_enabled": True, "used_dictionary": True, "used_yaml": True},
        "query_hints": {"candidate_group_dimensions": ["area", "cargo", "birth_month"]},
        "supports_sql_assisted": True,
        "domain_status": "active",
    }


class ChatRuntimeSqlAlignmentTests(SimpleTestCase):
    def _resolve_plan(
        self,
        *,
        message: str,
        session_context: dict | None = None,
    ):
        bootstrap = ChatApplicationService._bootstrap_classification(
            message=message,
            session_context=session_context or {},
        )
        resolved_intent = QueryIntentResolver().resolve(
            message=message,
            base_classification=bootstrap,
            semantic_context=_pilot_context(),
        )
        resolved_query = ResolvedQuerySpec(
            intent=resolved_intent,
            semantic_context=_pilot_context(),
            normalized_period={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )
        plan = QueryExecutionPlanner().plan(
            run_context=RunContext.create(message=message, session_id="sem-phase9-check", reset_memory=False),
            resolved_query=resolved_query,
        )
        return bootstrap, resolved_intent, plan

    def test_analytics_questions_do_not_activate_knowledge_governance(self):
        with patch.dict(
            "os.environ",
            {"IA_DEV_USE_OPENAI_CLASSIFIER": "0", "IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED": "0"},
            clear=False,
        ):
            classification = IntentClassifierService().classify("Que patrones existen por area, cargo y sede")
            bootstrap = ChatApplicationService._bootstrap_classification(
                message="Que patrones existen por area, cargo y sede",
                session_context={"last_domain": "ausentismo", "last_needs_database": True},
            )

        self.assertEqual(str(classification.get("intent") or ""), "empleados_query")
        self.assertEqual(str(classification.get("domain") or ""), "empleados")
        self.assertNotEqual(str(classification.get("intent") or ""), "knowledge_change_request")
        self.assertEqual(str(bootstrap.get("intent") or ""), "ausentismo_query")
        self.assertEqual(str(bootstrap.get("domain") or ""), "ausentismo")
        self.assertEqual(str(bootstrap.get("classifier_source") or ""), "bootstrap_session_continuity")

    def test_que_areas_tienen_mas_ausentismo_prefers_join_aware_sql(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_USE_OPENAI_CLASSIFIER": "0",
                "IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED": "0",
                "IA_DEV_QUERY_SQL_ASSISTED_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_ATTENDANCE_EMPLOYEES_PILOT_ENABLED": "1",
            },
            clear=False,
        ):
            _bootstrap, resolved_intent, plan = self._resolve_plan(
                message="Que areas tienen mas ausentismo",
            )

        self.assertEqual(str(resolved_intent.domain_code or ""), "ausentismo")
        self.assertEqual(plan.strategy, "sql_assisted")
        self.assertEqual(str((plan.metadata or {}).get("analytics_router_decision") or ""), "join_aware_sql")
        self.assertEqual(str((plan.metadata or {}).get("compiler") or ""), "join_aware_pilot")

    def test_active_domain_with_productive_pilot_still_allows_sql_assisted(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_QUERY_SQL_ASSISTED_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_ATTENDANCE_EMPLOYEES_PILOT_ENABLED": "1",
            },
            clear=False,
        ):
            _bootstrap, resolved_intent, _plan = self._resolve_plan(
                message="Que areas tienen mas ausentismo",
            )
            resolved_query = ResolvedQuerySpec(
                intent=resolved_intent,
                semantic_context={**_pilot_context(), "domain_status": "active"},
                normalized_period={"start_date": "2026-01-01", "end_date": "2026-01-31"},
            )
            decision = QueryExecutionPolicy().evaluate_sql_assisted(
                run_context=RunContext.create(message="Que areas tienen mas ausentismo", session_id="pilot-active", reset_memory=False),
                resolved_query=resolved_query,
            )

        self.assertTrue(decision.allowed)
        self.assertEqual(str(decision.reason or ""), "sql_assisted_allowed")

    def test_que_sedes_presentan_mas_ausencias_uses_join_aware_sql(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_USE_OPENAI_CLASSIFIER": "0",
                "IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED": "0",
                "IA_DEV_QUERY_SQL_ASSISTED_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_ATTENDANCE_EMPLOYEES_PILOT_ENABLED": "1",
            },
            clear=False,
        ):
            _bootstrap, resolved_intent, plan = self._resolve_plan(
                message="Que sedes presentan mas ausencias",
            )

        self.assertEqual(str(resolved_intent.domain_code or ""), "ausentismo")
        self.assertEqual(list(resolved_intent.group_by or []), ["sede"])
        self.assertEqual(str(resolved_intent.operation or ""), "aggregate")
        self.assertEqual(plan.strategy, "sql_assisted")
        self.assertEqual(str((plan.metadata or {}).get("analytics_router_decision") or ""), "join_aware_sql")
        self.assertEqual(str((plan.metadata or {}).get("compiler") or ""), "join_aware_pilot")
        self.assertEqual(list((plan.metadata or {}).get("dimensions_used") or []), ["sede"])
        self.assertEqual(str((plan.reason or "")), "pilot_join_aware_sede")
        self.assertIn(
            "gestionh_ausentismo.cedula = cinco_base_de_personal.cedula",
            list((plan.metadata or {}).get("relations_used") or []),
        )
        self.assertIn("zona_nodo", list((plan.metadata or {}).get("physical_columns_used") or []))

    def test_que_patrones_existen_por_area_cargo_y_sede_uses_sql_assisted_without_kpro(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_USE_OPENAI_CLASSIFIER": "0",
                "IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED": "0",
                "IA_DEV_QUERY_SQL_ASSISTED_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_ATTENDANCE_EMPLOYEES_PILOT_ENABLED": "1",
            },
            clear=False,
        ):
            bootstrap, resolved_intent, plan = self._resolve_plan(
                message="Que patrones existen por area, cargo y sede",
                session_context={"last_domain": "ausentismo", "last_needs_database": True},
            )

        self.assertEqual(str(bootstrap.get("intent") or ""), "ausentismo_query")
        self.assertEqual(str(resolved_intent.domain_code or ""), "ausentismo")
        self.assertEqual(str(resolved_intent.operation or ""), "aggregate")
        self.assertEqual(plan.strategy, "sql_assisted")
        self.assertEqual(str((plan.metadata or {}).get("analytics_router_decision") or ""), "join_aware_sql")
        self.assertEqual(str((plan.metadata or {}).get("compiler") or ""), "join_aware_pilot")

    def test_sql_assisted_fails_safe_when_dictionary_is_missing_requested_dimension(self):
        semantic_context = _pilot_context()
        semantic_context["allowed_columns"] = ["fecha_edit", "cedula", "area", "cargo"]
        semantic_context["column_profiles"] = [
            item for item in list(semantic_context.get("column_profiles") or [])
            if str(item.get("logical_name") or "") != "sede"
        ]
        resolved_query = ResolvedQuerySpec(
            intent=StructuredQueryIntent(
                raw_query="Que sedes presentan mas ausencias",
                domain_code="ausentismo",
                operation="aggregate",
                template_id="aggregate_by_group_and_period",
                group_by=["sede"],
                metrics=["count"],
                confidence=0.88,
            ),
            semantic_context=semantic_context,
            normalized_period={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )

        with patch.dict(
            "os.environ",
            {
                "IA_DEV_QUERY_SQL_ASSISTED_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_ATTENDANCE_EMPLOYEES_PILOT_ENABLED": "1",
            },
            clear=False,
        ):
            plan = QueryExecutionPlanner().plan(
                run_context=RunContext.create(message="Que sedes presentan mas ausencias", session_id="missing-sede", reset_memory=False),
                resolved_query=resolved_query,
            )

        self.assertEqual(plan.strategy, "fallback")
        self.assertTrue(
            str(plan.reason or "").startswith("sql_rejected:")
            or str(plan.reason or "") in {"no_allowed_dimension", "unsupported_dimension"}
        )

    def test_employee_birthdays_in_may_use_sql_assisted(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_USE_OPENAI_CLASSIFIER": "0",
                "IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED": "0",
                "IA_DEV_QUERY_SQL_ASSISTED_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_ATTENDANCE_EMPLOYEES_PILOT_ENABLED": "1",
            },
            clear=False,
        ):
            resolved_intent = QueryIntentResolver().resolve(
                message="Cumpleaños de mayo",
                base_classification={"domain": "general", "intent": "general_question"},
                semantic_context=_employee_birthday_context(),
            )
            resolved_query = ResolvedQuerySpec(
                intent=resolved_intent,
                semantic_context=_employee_birthday_context(),
                normalized_filters={"fnacimiento_month": "5", "estado": "ACTIVO"},
                normalized_period={},
            )
            plan = QueryExecutionPlanner().plan(
                run_context=RunContext.create(message="Cumpleaños de mayo", session_id="birthday-may", reset_memory=False),
                resolved_query=resolved_query,
            )

        self.assertEqual(str(resolved_intent.domain_code or ""), "empleados")
        self.assertEqual(plan.strategy, "sql_assisted")
        self.assertIn("MONTH(fnacimiento) = 5", str(plan.sql_query or ""))
        self.assertEqual(str((plan.metadata or {}).get("compiler") or ""), "employee_semantic_sql")

    def test_employee_birthdays_in_may_grouped_by_area_use_sql_assisted(self):
        with patch.dict(
            "os.environ",
            {
                "IA_DEV_USE_OPENAI_CLASSIFIER": "0",
                "IA_DEV_QUERY_INTELLIGENCE_OPENAI_ENABLED": "0",
                "IA_DEV_QUERY_SQL_ASSISTED_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_ATTENDANCE_EMPLOYEES_PILOT_ENABLED": "1",
            },
            clear=False,
        ):
            resolved_intent = QueryIntentResolver().resolve(
                message="cumpleanos de mayo por area",
                base_classification={"domain": "general", "intent": "general_question"},
                semantic_context=_employee_birthday_context(),
            )
            resolved_query = ResolvedQuerySpec(
                intent=resolved_intent,
                semantic_context=_employee_birthday_context(),
                normalized_filters={"fnacimiento_month": "5", "estado": "ACTIVO"},
                normalized_period={},
            )
            plan = QueryExecutionPlanner().plan(
                run_context=RunContext.create(message="cumpleanos de mayo por area", session_id="birthday-area", reset_memory=False),
                resolved_query=resolved_query,
            )

        self.assertEqual(str(resolved_intent.domain_code or ""), "empleados")
        self.assertEqual(str(resolved_intent.operation or ""), "aggregate")
        self.assertEqual(list(resolved_intent.group_by or []), ["area"])
        self.assertEqual(plan.strategy, "sql_assisted")
        self.assertIn("MONTH(fnacimiento) = 5", str(plan.sql_query or ""))
        self.assertIn("SELECT area AS area, COUNT(*) AS total_registros", str(plan.sql_query or ""))
        self.assertIn("GROUP BY area", str(plan.sql_query or ""))
        self.assertEqual(list((plan.metadata or {}).get("dimensions_used") or []), ["area"])
        self.assertEqual(str((plan.metadata or {}).get("compiler") or ""), "employee_semantic_sql")

    def test_pilot_report_counts_sql_assisted_and_physical_columns(self):
        observability = MagicMock()
        observability.list_events.return_value = [
            {
                "event_type": "runtime_response_resolved",
                "meta": {
                    "pilot_enabled": True,
                    "domain_resolved": "ausentismo",
                    "response_flow": "sql_assisted",
                    "compiler_used": "join_aware_pilot",
                    "original_question": "Que areas tienen mas ausentismo",
                    "columns_used": ["area", "cedula", "fecha_edit"],
                    "relations_used": ["gestionh_ausentismo.cedula = cinco_base_de_personal.cedula"],
                    "satisfaction_review": {"satisfied": True},
                    "insight_quality": "good",
                },
            },
            {
                "event_type": "runtime_response_resolved",
                "meta": {
                    "pilot_enabled": True,
                    "domain_resolved": "ausentismo",
                    "response_flow": "sql_assisted",
                    "compiler_used": "join_aware_pilot",
                    "original_question": "Que sedes presentan mas ausencias",
                    "columns_used": ["zona_nodo", "cedula", "fecha_edit"],
                    "relations_used": ["gestionh_ausentismo.cedula = cinco_base_de_personal.cedula"],
                    "satisfaction_review": {"satisfied": True},
                    "insight_quality": "good",
                },
            },
            {
                "event_type": "runtime_response_resolved",
                "meta": {
                    "pilot_enabled": True,
                    "domain_resolved": "ausentismo",
                    "response_flow": "sql_assisted",
                    "compiler_used": "join_aware_pilot",
                    "original_question": "Que patrones existen por area, cargo y sede",
                    "columns_used": ["area", "cargo", "zona_nodo", "cedula", "fecha_edit"],
                    "relations_used": ["gestionh_ausentismo.cedula = cinco_base_de_personal.cedula"],
                    "satisfaction_review": {"satisfied": True},
                    "insight_quality": "good",
                },
            },
        ]

        report = RuntimeGovernanceService(observability_service=observability).build_pilot_report(
            domain="ausentismo",
            days=7,
        )

        self.assertGreater(int(report.get("sql_assisted_count") or 0), 0)
        self.assertEqual(int(report.get("sql_assisted_count") or 0), 3)
        self.assertEqual(
            list(report.get("compiladores_usados") or []),
            [{"compiler": "join_aware_pilot", "count": 3}],
        )
        columnas = {item.get("column"): item.get("count") for item in list(report.get("columnas_usadas") or [])}
        self.assertIn("area", columnas)
        self.assertIn("cargo", columnas)
        self.assertIn("zona_nodo", columnas)
        self.assertNotIn("total_ausentismos", columnas)
        self.assertEqual(
            list(report.get("relaciones_usadas") or []),
            [{"relation": "gestionh_ausentismo.cedula = cinco_base_de_personal.cedula", "count": 3}],
        )

    def test_sql_assisted_response_keeps_chart_payload_when_group_dimension_is_null(self):
        planner = QueryExecutionPlanner()
        resolved_query = ResolvedQuerySpec(
            intent=QueryIntentResolver().resolve(
                message="Que sedes presentan mas ausencias",
                base_classification={"domain": "ausentismo", "intent": "ausentismo_query"},
                semantic_context=_pilot_context(),
            ),
            semantic_context=_pilot_context(),
            normalized_period={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )
        execution_plan = QueryExecutionPlan(
            strategy="sql_assisted",
            reason="pilot_join_aware_sede",
            domain_code="ausentismo",
            sql_query="SELECT zona_nodo AS sede, COUNT(*) AS total_ausentismos FROM demo GROUP BY zona_nodo",
            metadata={"compiler": "join_aware_pilot"},
        )

        response = planner._build_sql_response(
            run_context=RunContext.create(message="Que sedes presentan mas ausencias", session_id="null-sede", reset_memory=False),
            resolved_query=resolved_query,
            execution_plan=execution_plan,
            sql_query=str(execution_plan.sql_query or ""),
            rows=[{"sede": None, "total_ausentismos": 35}],
            columns=["sede", "total_ausentismos"],
            duration_ms=12,
            db_alias="default",
        )

        data = dict(response.get("data") or {})
        self.assertEqual(list(data.get("labels") or []), ["N/D"])
        self.assertTrue(bool(list(data.get("series") or [])))
        self.assertTrue(bool(list(data.get("charts") or [])))

    def test_query_intent_merge_guardrail_rejects_employee_filters_for_attendance_patterns(self):
        fallback = StructuredQueryIntent(
            raw_query="Que patrones existen por area, cargo y sede",
            domain_code="ausentismo",
            operation="aggregate",
            template_id="aggregate_by_group_and_period",
            filters={"indicador_ausentismo": "SI"},
            group_by=["area", "cargo", "sede"],
            metrics=["count"],
            confidence=0.72,
            source="rules",
            warnings=[],
        )
        llm = StructuredQueryIntent(
            raw_query=fallback.raw_query,
            domain_code="empleados",
            operation="count",
            template_id="count_entities_by_status",
            filters={"estado": "ACTIVO", "estado_empleado": "ACTIVO", "cargo": "y sede"},
            group_by=["area", "cargo", "sede"],
            metrics=["count"],
            confidence=0.91,
            source="openai",
            warnings=[],
        )

        merged = QueryIntentResolver._merge_intents(fallback=fallback, llm=llm)

        self.assertEqual(str(merged.domain_code or ""), "ausentismo")
        self.assertEqual(str(merged.operation or ""), "aggregate")
        self.assertEqual(str(merged.template_id or ""), "aggregate_by_group_and_period")
        self.assertEqual(dict(merged.filters or {}), {"indicador_ausentismo": "SI"})
