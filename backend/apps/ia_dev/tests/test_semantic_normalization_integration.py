from __future__ import annotations

import os
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    QueryExecutionPlan,
    ResolvedQuerySpec,
    SemanticNormalizationOutput,
    StructuredQueryIntent,
)
from apps.ia_dev.application.orchestration.chat_application_service import (
    ChatApplicationService,
)


class SemanticNormalizationIntegrationTests(SimpleTestCase):
    def _build_service(self, *, semantic_normalization_service):
        semantic_resolver = Mock()
        semantic_resolver.build_semantic_context.return_value = {
            "domain_code": "empleados",
            "tables": [{"table_name": "cinco_base_de_personal"}],
            "column_profiles": [],
            "dictionary": {"synonyms": []},
            "dictionary_seed": {"enabled": False, "status": "skipped"},
        }
        intent = StructuredQueryIntent(
            raw_query="cantidad empleados activos",
            domain_code="empleados",
            operation="count",
            template_id="count_entities_by_status",
            filters={},
            period={"label": "hoy", "start_date": "2026-04-18", "end_date": "2026-04-18"},
            group_by=[],
            metrics=["count"],
            confidence=0.9,
            source="rules",
        )
        semantic_resolver.resolve_query.return_value = ResolvedQuerySpec(
            intent=intent,
            semantic_context={"tables": [{"table_name": "cinco_base_de_personal"}]},
            normalized_filters={"estado": "ACTIVO"},
            normalized_period={"label": "hoy", "start_date": "2026-04-18", "end_date": "2026-04-18"},
            mapped_columns={"estado": "estado"},
            warnings=[],
        )
        intent_resolver = Mock()
        intent_resolver.resolve.return_value = intent
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
        return ChatApplicationService(
            semantic_business_resolver=semantic_resolver,
            query_intent_resolver=intent_resolver,
            query_execution_planner=execution_planner,
            semantic_normalization_service=semantic_normalization_service,
        )

    def test_flags_off_keeps_semantic_normalization_inactive(self):
        normalization = Mock()
        service = self._build_service(semantic_normalization_service=normalization)
        run_context = RunContext.create(message="cantidad empleados activos")
        with patch.dict(
            os.environ,
            {
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_MODE": "active",
                "IA_DEV_SEMANTIC_NORMALIZATION_ENABLED": "0",
                "IA_DEV_SEMANTIC_NORMALIZATION_SHADOW_ENABLED": "0",
            },
            clear=False,
        ):
            payload = service._resolve_query_intelligence(
                message="cantidad empleados activos",
                base_classification={"domain": "empleados", "intent": "empleados_query", "needs_database": True},
                run_context=run_context,
                observability=None,
            )
        normalization.normalize.assert_not_called()
        sn = dict(payload.get("semantic_normalization") or {})
        self.assertFalse(bool(sn.get("active")))
        self.assertFalse(bool(sn.get("shadow")))

    def test_shadow_mode_computes_without_altering_runtime_intent(self):
        output = SemanticNormalizationOutput(
            raw_query="cantidad personal activo",
            normalized_query="cantidad personal activo",
            canonical_query="cantidad empleados activo",
            semantic_aliases=[{"alias": "personal", "canonical": "empleados"}],
            candidate_domains=[{"domain": "empleados", "confidence": 0.82}],
            candidate_intents=[{"intent": "count", "confidence": 0.9}],
            candidate_entities=[],
            candidate_filters=[{"filter": "estado", "value": "ACTIVO", "confidence": 0.9}],
            capability_hints=[],
            ambiguities=[],
            llm_invoked=False,
            llm_mode="hybrid",
            normalization_status="deterministic_only",
            confidence=0.84,
            review_notes=["llm_decision:deterministic_sufficient"],
        )
        normalization = Mock()
        normalization.normalize.return_value = output
        service = self._build_service(semantic_normalization_service=normalization)
        run_context = RunContext.create(message="cantidad personal activo")
        with patch.dict(
            os.environ,
            {
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_MODE": "active",
                "IA_DEV_SEMANTIC_NORMALIZATION_ENABLED": "0",
                "IA_DEV_SEMANTIC_NORMALIZATION_SHADOW_ENABLED": "1",
            },
            clear=False,
        ):
            payload = service._resolve_query_intelligence(
                message="cantidad personal activo",
                base_classification={"domain": "general", "intent": "general_question", "needs_database": False},
                run_context=run_context,
                observability=None,
            )
        normalization.normalize.assert_called_once()
        self.assertEqual(str(payload.get("intent", {}).get("domain_code") or ""), "empleados")
        sn = dict(payload.get("semantic_normalization") or {})
        self.assertFalse(bool(sn.get("active")))
        self.assertTrue(bool(sn.get("shadow")))
        ab = dict(sn.get("ab_evaluation") or {})
        self.assertIn("off", ab)
        self.assertIn("on", ab)
        self.assertIn("llm_changed_canonical_query", ab)
        self.assertIn("llm_changed_domain", ab)
        self.assertIn("llm_changed_intent", ab)
        self.assertIn("llm_changed_filters", ab)
        self.assertIn("llm_improved_confidence", ab)
        self.assertEqual(str((ab.get("on") or {}).get("final_capability") or ""), "empleados.count.active.v1")
        self.assertTrue(str((ab.get("on") or {}).get("resolved_by") or ""))
