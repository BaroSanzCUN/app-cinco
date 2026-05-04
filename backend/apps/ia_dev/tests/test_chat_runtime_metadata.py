from __future__ import annotations

import os
import inspect
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.orchestration.chat_application_service import ChatApplicationService


class _ObservabilityStub:
    def __init__(self):
        self.events: list[dict] = []

    def record_event(self, *, event_type: str, source: str, meta: dict):
        self.events.append({"event_type": event_type, "source": source, "meta": dict(meta or {})})


class ChatRuntimeMetadataTests(SimpleTestCase):
    def test_attach_runtime_metadata_includes_task_state_and_flow(self):
        run_context = RunContext.create(message="x", session_id="sess-1", reset_memory=False)
        run_context.metadata["task_state"] = {
            "workflow_key": "task_runtime:run-1",
            "status": "completed",
        }
        run_context.metadata["intent_arbitration"] = {
            "heuristic_intent": "knowledge_change_request",
            "llm_intent": "aggregate",
            "final_intent": "analytics_query",
            "final_domain": "ausentismo",
            "confidence": 0.91,
            "reasoning_summary": "Consulta analitica sobre datos existentes.",
            "should_create_kpro": False,
            "should_use_sql_assisted": True,
        }
        run_context.metadata["query_intelligence"] = {
            "execution_plan": {
                "metadata": {
                    "compiler": "join_aware_pilot",
                    "analytics_router_decision": "join_aware_sql",
                }
            }
        }
        run_context.metadata["cleanup_guard"] = {
            "analytics_router_decision": "runtime_only_fallback",
            "legacy_analytics_isolated": True,
            "legacy_analytics_fallback_disabled": True,
            "blocked_legacy_fallback": True,
            "blocked_tool_ausentismo_service": True,
            "blocked_run_legacy_for_analytics": True,
            "runtime_only_fallback_reason": "missing_dictionary_relation",
            "fallback_reason": "pilot_relation_missing",
            "cleanup_phase": "phase_7",
        }
        run_context.metadata["runtime_compatibility"] = {
            "runtime_authority": "query_execution_planner",
            "planner_was_authority": True,
            "planner_selected_strategy": "sql_assisted",
            "legacy_capability_path_used": False,
            "routing_mode": "intent",
        }

        response = ChatApplicationService._attach_runtime_metadata(
            response={"orchestrator": {}, "data_sources": {}},
            run_context=run_context,
            response_flow="sql_assisted",
        )

        self.assertEqual(str((response.get("orchestrator") or {}).get("runtime_flow") or ""), "sql_assisted")
        self.assertEqual(str((response.get("orchestrator") or {}).get("arbitrated_intent") or ""), "analytics_query")
        self.assertEqual(str((response.get("orchestrator") or {}).get("final_intent") or ""), "analytics_query")
        self.assertEqual(str((response.get("orchestrator") or {}).get("final_domain") or ""), "ausentismo")
        self.assertEqual(str((response.get("orchestrator") or {}).get("compiler_used") or ""), "join_aware_pilot")
        self.assertEqual(str((response.get("orchestrator") or {}).get("analytics_router_decision") or ""), "join_aware_sql")
        self.assertEqual(str((response.get("orchestrator") or {}).get("fallback_reason") or ""), "pilot_relation_missing")
        self.assertEqual(str((response.get("task_state") or {}).get("workflow_key") or ""), "task_runtime:run-1")
        self.assertEqual(str(((response.get("data_sources") or {}).get("runtime") or {}).get("flow") or ""), "sql_assisted")
        self.assertEqual(
            str(((response.get("data_sources") or {}).get("runtime") or {}).get("runtime_authority") or ""),
            "query_execution_planner",
        )
        self.assertTrue(bool(((response.get("data_sources") or {}).get("runtime") or {}).get("planner_was_authority")))
        self.assertTrue(bool(((response.get("data_sources") or {}).get("runtime") or {}).get("blocked_legacy_fallback")))
        self.assertEqual(
            str(((response.get("data_sources") or {}).get("runtime") or {}).get("analytics_router_decision") or ""),
            "join_aware_sql",
        )
        self.assertEqual(str(((response.get("data_sources") or {}).get("runtime") or {}).get("final_domain") or ""), "ausentismo")
        self.assertEqual(
            str(((response.get("data_sources") or {}).get("runtime") or {}).get("fallback_reason") or ""),
            "pilot_relation_missing",
        )

    def test_build_runtime_compatibility_metadata_marks_legacy_path_usage(self):
        metadata = ChatApplicationService._build_runtime_compatibility_metadata(
            query_intelligence={"execution_plan": {"strategy": "fallback"}},
            route={
                "routing_mode": "capability",
                "runtime_authority": "query_execution_planner",
                "use_legacy": True,
            },
            execution_meta={"used_legacy": True},
        )

        self.assertTrue(bool(metadata.get("legacy_capability_path_used")))
        self.assertEqual(str(metadata.get("runtime_authority") or ""), "query_execution_planner")
        self.assertEqual(str(metadata.get("planner_selected_strategy") or ""), "fallback")
        self.assertTrue(bool(metadata.get("planner_was_authority")))
        self.assertEqual(str(metadata.get("routing_mode") or ""), "capability")

    def test_chat_application_service_source_does_not_import_legacy_capability_components(self):
        import apps.ia_dev.application.orchestration.chat_application_service as chat_module

        source = inspect.getsource(chat_module)
        self.assertNotIn("CapabilityRouter", source)
        self.assertNotIn("CapabilityPlanner", source)
        self.assertNotIn("IntentToCapabilityBridge", source)

    def test_proactive_loop_flag_off_keeps_loop_disabled(self):
        with patch.dict(
            os.environ,
            {
                "IA_DEV_ROUTING_MODE": "capability",
                "IA_DEV_PROACTIVE_LOOP_ENABLED": "0",
            },
            clear=False,
        ):
            run_context = RunContext.create(message="x", session_id="sess-2", reset_memory=False)
            self.assertFalse(ChatApplicationService._proactive_loop_enabled(run_context=run_context))

    def test_resolve_runtime_response_flow_covers_sql_handler_runtime_only_and_legacy(self):
        self.assertEqual(
            ChatApplicationService._resolve_runtime_response_flow(
                query_intelligence={"execution_plan": {"strategy": "sql_assisted"}},
                route={"execute_capability": False},
                response={"orchestrator": {"classifier_source": "query_intelligence_sql_assisted"}},
                execution_meta={},
            ),
            "sql_assisted",
        )
        self.assertEqual(
            ChatApplicationService._resolve_runtime_response_flow(
                query_intelligence={},
                route={"execute_capability": True},
                response={"orchestrator": {"classifier_source": "handler_runtime"}},
                execution_meta={},
            ),
            "handler",
        )
        self.assertEqual(
            ChatApplicationService._resolve_runtime_response_flow(
                query_intelligence={},
                route={"execute_capability": False},
                response={"orchestrator": {"classifier_source": "query_intelligence_runtime_only_fallback"}},
                execution_meta={"blocked_legacy_fallback": True},
            ),
            "runtime_only_fallback",
        )
        self.assertEqual(
            ChatApplicationService._resolve_runtime_response_flow(
                query_intelligence={},
                route={"execute_capability": False},
                response={"orchestrator": {"classifier_source": "general_answer"}},
                execution_meta={"used_legacy": True},
            ),
            "legacy_fallback",
        )

    def test_record_runtime_resolution_event_includes_compiler_and_satisfaction(self):
        observability = _ObservabilityStub()
        run_context = RunContext.create(message="x", session_id="sess-1", reset_memory=False)

        ChatApplicationService()._record_runtime_resolution_event(
            observability=observability,
            run_context=run_context,
            query_intelligence={
                "execution_plan": {
                    "metadata": {
                        "compiler": "join_aware_pilot",
                        "relations_used": ["gestionh_ausentismo.cedula = cinco_base_de_personal.cedula"],
                        "metric_used": "dias_perdidos",
                        "aggregation_used": "sum",
                        "dimensions_used": ["area"],
                        "declared_metric_source": "ai_dictionary.dd_campos",
                        "declared_dimensions_source": "ai_dictionary.dd_campos",
                    }
                },
                "resolved_query": {
                    "intent": {"domain_code": "ausentismo"},
                    "semantic_context": {
                        "tables": [
                            {"table_name": "gestionh_ausentismo"},
                            {"table_name": "cinco_base_de_personal"},
                        ],
                        "column_profiles": [
                            {"column_name": "fecha_edit"},
                            {"column_name": "cedula"},
                        ],
                        "source_of_truth": {
                            "used_dictionary": True,
                            "used_yaml": True,
                            "structural_source": "ai_dictionary",
                            "yaml_role": "narrative_only",
                            "yaml_structural_ignored": True,
                        },
                    },
                },
            },
            route={"reason": "query_intelligence_active_precomputed_response"},
            response={"orchestrator": {"classifier_source": "query_intelligence_sql_assisted"}},
            execution_meta={
                "analytics_router_decision": "join_aware_sql",
                "legacy_analytics_isolated": True,
                "fallback_reason": "",
                "legacy_analytics_fallback_disabled": True,
                "blocked_legacy_fallback": False,
                "blocked_tool_ausentismo_service": False,
                "blocked_run_legacy_for_analytics": False,
                "runtime_only_fallback_reason": "",
                "cleanup_phase": "phase_7",
            },
            response_flow="sql_assisted",
            satisfaction_snapshot={"satisfied": True, "gate_score": 0.88},
        )

        self.assertEqual(len(observability.events), 1)
        meta = dict(observability.events[0].get("meta") or {})
        self.assertEqual(str(meta.get("compiler_used") or ""), "join_aware_pilot")
        self.assertEqual(str(meta.get("domain_resolved") or ""), "ausentismo")
        self.assertEqual(str(meta.get("structural_source") or ""), "ai_dictionary")
        self.assertEqual(str(meta.get("yaml_role") or ""), "narrative_only")
        self.assertTrue(bool(meta.get("yaml_structural_ignored")))
        self.assertEqual(list(meta.get("tables_detected") or []), ["gestionh_ausentismo", "cinco_base_de_personal"])
        self.assertEqual(str(meta.get("metric_used") or ""), "dias_perdidos")
        self.assertEqual(str(meta.get("aggregation_used") or ""), "sum")
        self.assertEqual(list(meta.get("dimensions_used") or []), ["area"])
        self.assertTrue(bool((meta.get("satisfaction_review") or {}).get("satisfied")))
        self.assertEqual(str(meta.get("analytics_router_decision") or ""), "join_aware_sql")
        self.assertTrue(bool(meta.get("legacy_analytics_isolated")))
        self.assertEqual(str(meta.get("cleanup_phase") or ""), "phase_7")
