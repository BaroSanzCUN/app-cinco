from __future__ import annotations

import os
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    CanonicalResolvedQuery,
    QueryExecutionPlan,
    ResolvedQuerySpec,
    StructuredQueryIntent,
)
from apps.ia_dev.application.orchestration.chat_application_service import (
    ChatApplicationService,
)


class CanonicalResolutionIntegrationTests(SimpleTestCase):
    def _build_service(self, *, canonical_resolution_service):
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
        semantic_normalization_service = Mock()
        semantic_normalization_service.normalize.return_value = {
            "as_dict": lambda: {
                "raw_query": "cantidad empleados activos",
                "normalized_query": "cantidad empleados activos",
                "canonical_query": "cantidad empleados activos",
                "candidate_domains": [{"domain": "empleados", "confidence": 0.9}],
                "candidate_intents": [{"intent": "count", "confidence": 0.9}],
                "candidate_entities": [],
                "candidate_filters": [{"filter": "estado", "value": "ACTIVO"}],
                "capability_hints": [],
                "semantic_aliases": [],
                "ambiguities": [],
                "llm_invoked": False,
                "llm_mode": "hybrid",
                "normalization_status": "deterministic_only",
                "confidence": 0.9,
                "review_notes": [],
            }
        }
        # Ensure robust payload with an object exposing as_dict.
        class _Out:
            @staticmethod
            def as_dict():
                return {
                    "raw_query": "cantidad empleados activos",
                    "normalized_query": "cantidad empleados activos",
                    "canonical_query": "cantidad empleados activos",
                    "candidate_domains": [{"domain": "empleados", "confidence": 0.9}],
                    "candidate_intents": [{"intent": "count", "confidence": 0.9}],
                    "candidate_entities": [],
                    "candidate_filters": [{"filter": "estado", "value": "ACTIVO"}],
                    "capability_hints": [],
                    "semantic_aliases": [],
                    "ambiguities": [],
                    "llm_invoked": False,
                    "llm_mode": "hybrid",
                    "normalization_status": "deterministic_only",
                    "confidence": 0.9,
                    "review_notes": [],
                }

        semantic_normalization_service.normalize.return_value = _Out()
        return ChatApplicationService(
            semantic_business_resolver=semantic_resolver,
            query_intent_resolver=intent_resolver,
            query_execution_planner=execution_planner,
            semantic_normalization_service=semantic_normalization_service,
            canonical_resolution_service=canonical_resolution_service,
        )

    def test_shadow_mode_records_metadata_without_changing_runtime_intent(self):
        canonical = Mock()
        canonical.resolve.return_value = CanonicalResolvedQuery(
            raw_query="cantidad empleados activos",
            canonical_query="cantidad empleados activos",
            domain_code="empleados",
            intent_code="count",
            capability_code="empleados.count.active.v1",
            entities=[],
            filters=[{"filter": "estado", "value": "ACTIVO"}],
            confidence=0.93,
            resolution_evidence=[{"source": "capability_exact_match", "precedence": 1}],
            conflicts=[],
        )
        service = self._build_service(canonical_resolution_service=canonical)
        run_context = RunContext.create(message="cantidad empleados activos")
        with patch.dict(
            os.environ,
            {
                "IA_DEV_QUERY_INTELLIGENCE_ENABLED": "1",
                "IA_DEV_QUERY_INTELLIGENCE_MODE": "active",
                "IA_DEV_SEMANTIC_NORMALIZATION_ENABLED": "1",
                "IA_DEV_CANONICAL_RESOLUTION_ENABLED": "0",
                "IA_DEV_CANONICAL_RESOLUTION_SHADOW_ENABLED": "1",
            },
            clear=False,
        ):
            payload = service._resolve_query_intelligence(
                message="cantidad empleados activos",
                base_classification={"domain": "general", "intent": "general_question", "needs_database": False},
                run_context=run_context,
                observability=None,
            )
        canonical.resolve.assert_called_once()
        self.assertEqual(str(payload.get("intent", {}).get("domain_code") or ""), "empleados")
        canonical_meta = dict(payload.get("canonical_resolution") or {})
        self.assertFalse(bool(canonical_meta.get("active")))
        self.assertTrue(bool(canonical_meta.get("shadow")))
