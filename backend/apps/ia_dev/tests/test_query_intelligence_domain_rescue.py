from __future__ import annotations

import os
from unittest.mock import Mock, patch

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


class _ObservabilityStub:
    def __init__(self):
        self.events: list[dict] = []

    def record_event(self, *, event_type: str, source: str, meta: dict):
        self.events.append(
            {
                "event_type": event_type,
                "source": source,
                "meta": dict(meta or {}),
            }
        )


class QueryIntelligenceDomainRescueTests(SimpleTestCase):
    def test_resolve_query_intelligence_rescues_general_to_empleados(self):
        semantic_resolver = Mock()
        semantic_resolver.build_semantic_context.return_value = {
            "domain_code": "empleados",
            "tables": [{"table_name": "cinco_base_de_personal"}],
            "column_profiles": [],
            "dictionary_seed": {"enabled": False, "status": "skipped"},
        }
        resolved_intent = StructuredQueryIntent(
            raw_query="¿Cuántos colaboradores habilitados tenemos hoy?",
            domain_code="empleados",
            operation="count",
            template_id="count_entities_by_status",
            filters={},
            period={"label": "hoy", "start_date": "2026-04-16", "end_date": "2026-04-16"},
            group_by=[],
            metrics=["count"],
            confidence=0.9,
        )
        semantic_resolver.resolve_query.return_value = ResolvedQuerySpec(
            intent=resolved_intent,
            semantic_context={"tables": [{"table_name": "cinco_base_de_personal"}]},
            normalized_filters={"estado": "ACTIVO"},
            normalized_period={"label": "hoy", "start_date": "2026-04-16", "end_date": "2026-04-16"},
            mapped_columns={"estado": "estado"},
            warnings=[],
        )

        intent_resolver = Mock()
        intent_resolver.resolve.return_value = resolved_intent

        execution_planner = Mock()
        execution_planner.plan.return_value = QueryExecutionPlan(
            strategy="capability",
            reason="capability_selected_from_query_intelligence",
            domain_code="empleados",
            capability_id="empleados.count.active.v1",
            constraints={"filters": {"estado": "ACTIVO"}},
            policy={"allowed": True},
            metadata={"operation": "count"},
        )

        service = ChatApplicationService(
            semantic_business_resolver=semantic_resolver,
            query_intent_resolver=intent_resolver,
            query_execution_planner=execution_planner,
        )
        run_context = RunContext.create(message="¿Cuántos colaboradores habilitados tenemos hoy?")
        observability = _ObservabilityStub()

        with patch.dict(
            os.environ,
            {
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_MODE": "active",
            },
            clear=False,
        ):
            payload = service._resolve_query_intelligence(
                message="¿Cuántos colaboradores habilitados tenemos hoy?",
                base_classification={
                    "domain": "general",
                    "intent": "general_question",
                    "needs_database": False,
                },
                run_context=run_context,
                observability=observability,
            )

        self.assertEqual(payload.get("mode"), "active")
        self.assertEqual(str(payload.get("execution_plan", {}).get("strategy") or ""), "capability")
        self.assertNotEqual(str(payload.get("execution_plan", {}).get("strategy") or ""), "ask_context")

        called_domain = str(semantic_resolver.build_semantic_context.call_args.kwargs.get("domain_code") or "")
        self.assertEqual(called_domain, "empleados")
        self.assertTrue(any(item.get("event_type") == "query_domain_rescued" for item in observability.events))
