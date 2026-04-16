from __future__ import annotations

import copy
import os
from datetime import datetime, timezone
from typing import Any

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.contracts.chat_contracts import ensure_chat_response_contract
from apps.ia_dev.application.policies.policy_guard import PolicyDecision


class LegacyResponseAssembler:
    def assemble(
        self,
        *,
        legacy_response: dict[str, Any],
        run_context: RunContext,
        planned_capability: dict[str, Any],
        route: dict[str, Any],
        policy_decision: PolicyDecision,
        divergence: dict[str, Any],
        memory_effects: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        # Defensive deep-copy to avoid shared nested references between
        # `legacy_response` and metadata snapshots (e.g. query_intelligence.precomputed_response).
        # Shared references can become circular once we inject capability_shadow into orchestrator.
        response = ensure_chat_response_contract(copy.deepcopy(legacy_response))

        # Always expose memory loop outputs for incremental frontend adoption.
        effects = copy.deepcopy(dict(memory_effects or {}))
        existing_actions = list(response.get("actions") or [])
        injected_actions = list(effects.get("actions") or [])
        if injected_actions:
            existing_actions.extend(injected_actions)
        response["actions"] = existing_actions
        response["memory_candidates"] = list(effects.get("memory_candidates") or [])
        response["pending_proposals"] = list(effects.get("pending_proposals") or [])
        self._inject_query_intelligence_semantic_diagnostics(
            response=response,
            run_context=run_context,
        )
        self._inject_cause_diagnostics_trace(
            response=response,
            run_context=run_context,
        )

        if not run_context.is_shadow_mode and not run_context.is_capability_mode_requested:
            return response

        orchestrator = copy.deepcopy(response.get("orchestrator") or {})
        proactive_loop = copy.deepcopy(dict(run_context.metadata.get("proactive_loop") or {}))
        query_intelligence = copy.deepcopy(dict(run_context.metadata.get("query_intelligence") or {}))
        orchestrator["capability_shadow"] = {
            "run_id": run_context.run_id,
            "trace_id": run_context.trace_id,
            "routing_mode": run_context.routing_mode,
            "planned_capability": copy.deepcopy(planned_capability),
            "route": copy.deepcopy(route),
            "policy": {
                "action": policy_decision.action.value,
                "policy_id": policy_decision.policy_id,
                "reason": policy_decision.reason,
                "metadata": dict(policy_decision.metadata or {}),
            },
            "divergence": copy.deepcopy(divergence),
            "memory": {
                "candidate_count": len(response.get("memory_candidates") or []),
                "pending_proposals_count": len(response.get("pending_proposals") or []),
            },
            "proactive_loop": proactive_loop,
            "query_intelligence": query_intelligence,
        }
        response["orchestrator"] = orchestrator

        trace = copy.deepcopy(response.get("trace") or [])
        trace.append(
            self._trace_event(
                phase="capability_planner",
                status="ok",
                detail={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "planned_capability_id": planned_capability.get("capability_id"),
                    "reason": planned_capability.get("reason"),
                },
            )
        )
        trace.append(
            self._trace_event(
                phase="policy_guard",
                status="ok",
                detail={
                    "action": policy_decision.action.value,
                    "policy_id": policy_decision.policy_id,
                    "reason": policy_decision.reason,
                },
            )
        )
        trace.append(
            self._trace_event(
                phase="capability_router",
                status="ok",
                detail=route,
            )
        )
        trace.append(
            self._trace_event(
                phase="capability_divergence",
                status="warning" if divergence.get("diverged") else "ok",
                detail=divergence,
            )
        )
        if response.get("memory_candidates"):
            trace.append(
                self._trace_event(
                    phase="memory_feedback_loop",
                    status="ok",
                    detail={
                        "candidate_count": len(response.get("memory_candidates") or []),
                        "pending_count": len(response.get("pending_proposals") or []),
                    },
                )
            )
        if proactive_loop:
            trace.append(
                self._trace_event(
                    phase="proactive_loop",
                    status="ok" if not proactive_loop.get("used_legacy") else "warning",
                    detail={
                        "enabled": bool(proactive_loop.get("enabled")),
                        "iterations_ran": int(proactive_loop.get("iterations_ran") or 0),
                        "max_iterations": int(proactive_loop.get("max_iterations") or 0),
                        "selected_capability_id": proactive_loop.get("selected_capability_id"),
                        "used_legacy": bool(proactive_loop.get("used_legacy")),
                    },
                )
            )
        response["trace"] = trace
        return response

    def _inject_cause_diagnostics_trace(
        self,
        *,
        response: dict[str, Any],
        run_context: RunContext,
    ) -> None:
        data = dict(response.get("data") or {})
        cause_meta = dict(data.get("cause_generation_meta") or {})
        if not cause_meta:
            return

        trace = copy.deepcopy(response.get("trace") or [])
        if any(str(item.get("phase") or "") == "cause_diagnostics" for item in trace if isinstance(item, dict)):
            response["trace"] = trace
            return

        policy_decision = dict(cause_meta.get("policy_decision") or {})
        validation_errors = [
            str(item or "").strip()
            for item in list(cause_meta.get("validation_errors") or [])
            if str(item or "").strip()
        ]
        try:
            confidence = float(cause_meta.get("confidence") or 0.0)
        except Exception:
            confidence = 0.0
        try:
            top_pct = float(cause_meta.get("top_pct") or 0.0)
        except Exception:
            top_pct = 0.0

        trace.append(
            self._trace_event(
                phase="cause_diagnostics",
                status="ok" if str(cause_meta.get("generator") or "") == "openai" else "warning",
                detail={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "generator": str(cause_meta.get("generator") or ""),
                    "confidence": confidence,
                    "validated": bool(cause_meta.get("validated")),
                    "fallback_reason": str(cause_meta.get("fallback_reason") or ""),
                    "validation_errors": validation_errors,
                    "prompt_hash": str(cause_meta.get("prompt_hash") or ""),
                    "top_group": str(cause_meta.get("top_group") or ""),
                    "top_pct": top_pct,
                    "policy_reason": str(policy_decision.get("reason") or ""),
                    "policy_selected_generator": str(policy_decision.get("selected_generator") or ""),
                    "policy_allowed": bool(policy_decision.get("allowed")),
                },
            )
        )
        response["trace"] = trace

    def _inject_query_intelligence_semantic_diagnostics(
        self,
        *,
        response: dict[str, Any],
        run_context: RunContext,
    ) -> None:
        enabled = str(
            os.getenv("IA_DEV_QUERY_INTELLIGENCE_RESPONSE_DIAGNOSTICS_ENABLED", "1") or "1"
        ).strip().lower() in {"1", "true", "yes", "on"}
        if not enabled:
            return

        metadata = copy.deepcopy(dict(run_context.metadata.get("query_intelligence") or {}))
        if not metadata:
            return

        mode = str(metadata.get("mode") or "off").strip().lower()
        resolved_query = dict(metadata.get("resolved_query") or {})
        execution_plan = dict(metadata.get("execution_plan") or {})
        semantic_diagnostics = self._build_semantic_diagnostics_payload(
            resolved_query=resolved_query,
            execution_plan=execution_plan,
            mode=mode,
        )

        data_sources = dict(response.get("data_sources") or {})
        qi_source = dict(data_sources.get("query_intelligence") or {})
        if "ok" not in qi_source:
            qi_source["ok"] = mode != "off"
        qi_source["mode"] = mode
        if execution_plan:
            qi_source["strategy"] = str(execution_plan.get("strategy") or "")
        qi_source["semantic_diagnostics"] = semantic_diagnostics
        data_sources["query_intelligence"] = qi_source
        response["data_sources"] = data_sources

    def _build_semantic_diagnostics_payload(
        self,
        *,
        resolved_query: dict[str, Any],
        execution_plan: dict[str, Any],
        mode: str,
    ) -> dict[str, Any]:
        intent = dict(resolved_query.get("intent") or {})
        semantic_context = dict(resolved_query.get("semantic_context") or {})
        resolved_semantic = dict(semantic_context.get("resolved_semantic") or {})
        semantic_events = list(semantic_context.get("semantic_events") or [])
        normalized_filters = dict(resolved_query.get("normalized_filters") or {})
        mapped_columns = dict(resolved_query.get("mapped_columns") or {})

        filter_resolutions = [item for item in list(resolved_semantic.get("filters") or []) if isinstance(item, dict)]
        group_resolutions = [item for item in list(resolved_semantic.get("group_by") or []) if isinstance(item, dict)]
        metric_resolutions = [item for item in list(resolved_semantic.get("metrics") or []) if isinstance(item, dict)]

        synonym_matches = self._collect_synonym_matches(
            filter_resolutions=filter_resolutions,
            group_resolutions=group_resolutions,
            metric_resolutions=metric_resolutions,
            semantic_events=semantic_events,
        )
        column_actions = self._collect_column_actions(
            filter_resolutions=filter_resolutions,
            group_resolutions=group_resolutions,
            metric_resolutions=metric_resolutions,
        )
        unresolved_terms = self._collect_unresolved_terms(
            intent=intent,
            filter_resolutions=filter_resolutions,
            group_resolutions=group_resolutions,
            metric_resolutions=metric_resolutions,
        )
        search_bases = self._collect_search_bases(
            semantic_context=semantic_context,
            normalized_filters=normalized_filters,
            mapped_columns=mapped_columns,
        )

        return {
            "mode": mode,
            "domain_code": str(intent.get("domain_code") or ""),
            "operation": str(intent.get("operation") or ""),
            "template_id": str(intent.get("template_id") or ""),
            "strategy": str(execution_plan.get("strategy") or ""),
            "synonyms_applied": synonym_matches,
            "column_actions": column_actions,
            "unresolved_terms": unresolved_terms,
            "search_bases": search_bases,
            "warnings": list(resolved_query.get("warnings") or []),
        }

    @staticmethod
    def _normalize_token(value: str) -> str:
        return str(value or "").strip().lower()

    def _collect_synonym_matches(
        self,
        *,
        filter_resolutions: list[dict[str, Any]],
        group_resolutions: list[dict[str, Any]],
        metric_resolutions: list[dict[str, Any]],
        semantic_events: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []

        def add_from_resolution(scope: str, rows: list[dict[str, Any]]) -> None:
            for row in rows:
                requested = self._normalize_token(str(row.get("requested_term") or ""))
                canonical = self._normalize_token(str(row.get("canonical_term") or ""))
                if not requested or not canonical or requested == canonical:
                    continue
                matches.append(
                    {
                        "scope": scope,
                        "requested_term": requested,
                        "canonical_term": canonical,
                        "table_name": str(row.get("table_name") or ""),
                        "column_name": str(row.get("column_name") or ""),
                        "source": "ai_dictionary.dd_sinonimos_or_aliases",
                    }
                )

        add_from_resolution("filter", filter_resolutions)
        add_from_resolution("group_by", group_resolutions)
        add_from_resolution("metric", metric_resolutions)

        for event in semantic_events:
            if not isinstance(event, dict):
                continue
            if str(event.get("event_type") or "").strip() != "semantic_status_resolved_from_dictionary":
                continue
            matched_token = self._normalize_token(str(event.get("matched_token") or ""))
            status_value = str(event.get("status_value") or "").strip().upper()
            status_key = str(event.get("status_key") or "estado").strip().lower()
            if not matched_token or not status_value:
                continue
            matches.append(
                {
                    "scope": "filter",
                    "requested_term": matched_token,
                    "canonical_term": status_value,
                    "column_name": status_key,
                    "source": "ai_dictionary.dd_sinonimos+dd_campos",
                }
            )

        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in matches:
            key = "|".join(
                [
                    str(item.get("scope") or ""),
                    str(item.get("requested_term") or ""),
                    str(item.get("canonical_term") or ""),
                    str(item.get("column_name") or ""),
                ]
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @staticmethod
    def _collect_column_actions(
        *,
        filter_resolutions: list[dict[str, Any]],
        group_resolutions: list[dict[str, Any]],
        metric_resolutions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []

        def add(scope: str, action: str, rows: list[dict[str, Any]]) -> None:
            for row in rows:
                actions.append(
                    {
                        "scope": scope,
                        "action": action,
                        "requested_term": str(row.get("requested_term") or ""),
                        "canonical_term": str(row.get("canonical_term") or ""),
                        "table_name": str(row.get("table_name") or ""),
                        "column_name": str(row.get("column_name") or ""),
                        "supports_filter": bool(row.get("supports_filter")),
                        "supports_group_by": bool(row.get("supports_group_by")),
                        "supports_metric": bool(row.get("supports_metric")),
                        "is_identifier": bool(row.get("is_identifier")),
                        "is_chart_dimension": bool(row.get("is_chart_dimension")),
                        "is_chart_measure": bool(row.get("is_chart_measure")),
                    }
                )

        add("filter", "mapped_filter", filter_resolutions)
        add("group_by", "mapped_group_by", group_resolutions)
        add("metric", "mapped_metric", metric_resolutions)
        return actions

    def _collect_unresolved_terms(
        self,
        *,
        intent: dict[str, Any],
        filter_resolutions: list[dict[str, Any]],
        group_resolutions: list[dict[str, Any]],
        metric_resolutions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        unresolved: list[dict[str, Any]] = []

        resolved_filter_terms = {
            self._normalize_token(str(item.get("requested_term") or ""))
            for item in filter_resolutions
            if isinstance(item, dict)
        }
        resolved_group_terms = {
            self._normalize_token(str(item.get("requested_term") or ""))
            for item in group_resolutions
            if isinstance(item, dict)
        }
        resolved_metric_terms = {
            self._normalize_token(str(item.get("requested_term") or ""))
            for item in metric_resolutions
            if isinstance(item, dict)
        }

        for key in dict(intent.get("filters") or {}).keys():
            token = self._normalize_token(str(key))
            if token and token not in resolved_filter_terms:
                unresolved.append(
                    {
                        "scope": "filter",
                        "requested_term": token,
                        "reason": "no_semantic_column_match",
                        "searched_in": [
                            "ai_dictionary.dd_sinonimos",
                            "ai_dictionary.dd_campos",
                            "domain_runtime.column_profiles",
                        ],
                    }
                )

        for key in list(intent.get("group_by") or []):
            token = self._normalize_token(str(key))
            if token and token not in resolved_group_terms:
                unresolved.append(
                    {
                        "scope": "group_by",
                        "requested_term": token,
                        "reason": "group_dimension_not_resolved",
                        "searched_in": [
                            "ai_dictionary.dd_sinonimos",
                            "ai_dictionary.dd_campos",
                            "domain_runtime.column_profiles",
                        ],
                    }
                )

        for key in list(intent.get("metrics") or []):
            token = self._normalize_token(str(key))
            if token and token not in {"count"} and token not in resolved_metric_terms:
                unresolved.append(
                    {
                        "scope": "metric",
                        "requested_term": token,
                        "reason": "metric_not_resolved",
                        "searched_in": [
                            "ai_dictionary.dd_sinonimos",
                            "ai_dictionary.dd_campos",
                            "domain_runtime.column_profiles",
                        ],
                    }
                )
        return unresolved

    @staticmethod
    def _collect_search_bases(
        *,
        semantic_context: dict[str, Any],
        normalized_filters: dict[str, Any],
        mapped_columns: dict[str, Any],
    ) -> dict[str, Any]:
        dictionary_meta = dict(semantic_context.get("dictionary_meta") or {})
        dictionary_domain = dict(dictionary_meta.get("domain") or {})
        tables = [item for item in list(semantic_context.get("tables") or []) if isinstance(item, dict)]
        operational_tables: list[str] = []
        database_names: set[str] = set()
        for row in tables:
            table_fqn = str(row.get("table_fqn") or "").strip()
            table_name = str(row.get("table_name") or "").strip()
            if table_fqn:
                operational_tables.append(table_fqn)
                if "." in table_fqn:
                    database_names.add(str(table_fqn.split(".", 1)[0] or "").strip())
            elif table_name:
                operational_tables.append(table_name)
        if not database_names:
            for table in operational_tables:
                if "." in table:
                    database_names.add(str(table.split(".", 1)[0] or "").strip())
        return {
            "ai_dictionary": {
                "database_alias": str(os.getenv("IA_DEV_DB_ALIAS", "default") or "default"),
                "dictionary_table": str(dictionary_meta.get("dictionary_table") or ""),
                "schema": str(dictionary_meta.get("schema") or ""),
                "domain_code": str(dictionary_domain.get("code") or ""),
                "domain_name": str(dictionary_domain.get("name") or ""),
                "domain_matched": bool(dictionary_domain.get("matched")),
                "searched_tables": [
                    "dd_dominios",
                    "dd_tablas",
                    "dd_campos",
                    "dd_relaciones",
                    "dd_reglas",
                    "dd_sinonimos",
                ],
            },
            "operational_context": {
                "tables_considered": operational_tables[:20],
                "databases_detected": [item for item in sorted(database_names) if item],
                "filters_normalized": dict(normalized_filters or {}),
                "mapped_columns": dict(mapped_columns or {}),
            },
        }

    @staticmethod
    def _trace_event(*, phase: str, status: str, detail: dict[str, Any]) -> dict[str, Any]:
        return {
            "phase": phase,
            "status": status,
            "at": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
            "active_nodes": ["q", "gpt", "route"],
        }
