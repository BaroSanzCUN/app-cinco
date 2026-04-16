from __future__ import annotations

import logging
import os
import re
import unicodedata
from typing import Any, Callable

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.delegation.delegation_coordinator import (
    DelegationCoordinator,
)
from apps.ia_dev.application.memory.chat_memory_runtime_service import (
    ChatMemoryRuntimeService,
)
from apps.ia_dev.application.orchestration.response_assembler import (
    LegacyResponseAssembler,
)
from apps.ia_dev.application.contracts.query_intelligence_contracts import (
    QueryExecutionPlan,
    ResolvedQuerySpec,
    StructuredQueryIntent,
)
from apps.ia_dev.application.policies.policy_guard import PolicyGuard
from apps.ia_dev.application.routing.capability_catalog import CapabilityCatalog
from apps.ia_dev.application.routing.capability_planner import CapabilityPlanner
from apps.ia_dev.application.routing.capability_router import CapabilityRouter
from apps.ia_dev.application.routing.intent_to_capability_bridge import (
    IntentToCapabilityBridge,
)
from apps.ia_dev.application.semantic.query_execution_planner import QueryExecutionPlanner
from apps.ia_dev.application.semantic.query_intent_resolver import QueryIntentResolver
from apps.ia_dev.application.semantic.query_pattern_memory_service import QueryPatternMemoryService
from apps.ia_dev.application.semantic.result_satisfaction_validator import (
    ResultSatisfactionValidator,
)
from apps.ia_dev.application.semantic.semantic_business_resolver import SemanticBusinessResolver
from apps.ia_dev.services.memory_service import SessionMemoryStore


logger = logging.getLogger(__name__)


class ChatApplicationService:
    def __init__(
        self,
        *,
        catalog: CapabilityCatalog | None = None,
        planner: CapabilityPlanner | None = None,
        router: CapabilityRouter | None = None,
        bridge: IntentToCapabilityBridge | None = None,
        policy_guard: PolicyGuard | None = None,
        response_assembler: LegacyResponseAssembler | None = None,
        memory_runtime: ChatMemoryRuntimeService | None = None,
        delegation_coordinator: DelegationCoordinator | None = None,
        semantic_business_resolver: SemanticBusinessResolver | None = None,
        query_intent_resolver: QueryIntentResolver | None = None,
        query_execution_planner: QueryExecutionPlanner | None = None,
        result_satisfaction_validator: ResultSatisfactionValidator | None = None,
        query_pattern_memory_service: QueryPatternMemoryService | None = None,
    ):
        self.catalog = catalog or CapabilityCatalog()
        self.bridge = bridge or IntentToCapabilityBridge()
        self.planner = planner or CapabilityPlanner(catalog=self.catalog, bridge=self.bridge)
        self.router = router or CapabilityRouter()
        self.policy_guard = policy_guard or PolicyGuard()
        self.response_assembler = response_assembler or LegacyResponseAssembler()
        self.memory_runtime = memory_runtime or ChatMemoryRuntimeService()
        self.delegation_coordinator = delegation_coordinator or DelegationCoordinator()
        self.semantic_business_resolver = semantic_business_resolver or SemanticBusinessResolver()
        self.query_intent_resolver = query_intent_resolver or QueryIntentResolver()
        self.query_execution_planner = query_execution_planner or QueryExecutionPlanner(catalog=self.catalog)
        self.result_satisfaction_validator = result_satisfaction_validator or ResultSatisfactionValidator()
        self.query_pattern_memory_service = query_pattern_memory_service or QueryPatternMemoryService()

    def run(
        self,
        *,
        message: str,
        session_id: str | None,
        reset_memory: bool,
        legacy_runner: Callable[..., dict[str, Any]],
        observability=None,
        actor_user_key: str | None = None,
    ) -> dict[str, Any]:
        run_context = RunContext.create(
            message=message,
            session_id=session_id,
            reset_memory=reset_memory,
        )
        session_context: dict[str, Any] = {}
        if run_context.session_id and not run_context.reset_memory:
            try:
                session_context = SessionMemoryStore.get_context(run_context.session_id)
            except Exception:
                session_context = {}
        user_key = self._resolve_user_key(actor_user_key=actor_user_key, run_context=run_context)

        pre_classification = self._bootstrap_classification(
            message=message,
            session_context=session_context,
        )
        query_intelligence = self._resolve_query_intelligence(
            message=message,
            base_classification=pre_classification,
            run_context=run_context,
            observability=observability,
        )
        query_intelligence_mode = str(query_intelligence.get("mode") or "off")
        classification_override = dict(query_intelligence.get("classification_override") or {})
        if query_intelligence_mode == "active" and classification_override:
            pre_classification = {
                **pre_classification,
                **classification_override,
            }
        bootstrap_plan = self.planner.plan_from_legacy(
            message=message,
            classification=pre_classification,
        )
        pre_memory_context = self.memory_runtime.load_context_for_chat(
            user_key=user_key,
            domain_code=self._domain_code_from_capability(bootstrap_plan),
            capability_id=str(bootstrap_plan.get("capability_id") or "").strip() or None,
            run_context=run_context,
            observability=observability,
        )
        memory_hints = self._extract_memory_hints(pre_memory_context)
        workflow_hints = self._load_workflow_hints(user_key=user_key)
        run_context.metadata["memory_context"] = {
            "user_key": user_key,
            "session_context": {
                "last_domain": session_context.get("last_domain"),
                "last_intent": session_context.get("last_intent"),
                "last_output_mode": session_context.get("last_output_mode"),
                "last_period_start": session_context.get("last_period_start"),
                "last_period_end": session_context.get("last_period_end"),
            },
            "flags": dict(pre_memory_context.get("flags") or {}),
            "preloaded": {
                "user_memory_count": len(pre_memory_context.get("user_memory") or []),
                "business_memory_count": len(pre_memory_context.get("business_memory") or []),
                "domain_code": self._domain_code_from_capability(bootstrap_plan),
                "capability_id": bootstrap_plan.get("capability_id"),
            },
            "hints": memory_hints,
            "workflow_hints": workflow_hints,
        }

        candidate_plans = self._plan_candidates(
            message=message,
            classification=pre_classification,
            planning_context={
                "memory_hints": memory_hints,
                "workflow_hints": workflow_hints,
                "routing_mode": run_context.routing_mode,
                "query_intelligence": query_intelligence,
            },
            fallback_plan=bootstrap_plan,
        )
        candidate_plans = [
            self._apply_attendance_memory_hints(
                message=message,
                planned_capability=plan,
                memory_context=pre_memory_context,
                run_context=run_context,
                observability=observability,
            )
            for plan in candidate_plans
        ]
        candidate_plans = self._apply_query_intelligence_plan_overrides(
            candidate_plans=candidate_plans,
            fallback_plan=bootstrap_plan,
            query_intelligence=query_intelligence,
            classification=pre_classification,
        )
        run_context.metadata["planned_candidates"] = [
            {
                "capability_id": str(item.get("capability_id") or ""),
                "reason": str(item.get("reason") or ""),
                "candidate_rank": int(item.get("candidate_rank") or 0),
                "candidate_score": int(item.get("candidate_score") or 0),
            }
            for item in candidate_plans
        ]

        precomputed_response = dict(query_intelligence.get("precomputed_response") or {})

        delegation_decision = {
            "mode": "off",
            "should_delegate": False,
            "plan_reason": "query_intelligence_precomputed_response",
            "selected_domains": [],
            "tasks": [],
            "executed": False,
            "response": None,
            "warnings": [],
        }
        if not precomputed_response:
            delegation_decision = self.delegation_coordinator.plan_and_maybe_execute(
                message=message,
                classification=pre_classification,
                planned_candidates=candidate_plans,
                run_context=run_context,
                observability=observability,
            )
        run_context.metadata["delegation"] = {
            "mode": str(delegation_decision.get("mode") or "off"),
            "should_delegate": bool(delegation_decision.get("should_delegate")),
            "plan_reason": str(delegation_decision.get("plan_reason") or ""),
            "selected_domains": list(delegation_decision.get("selected_domains") or []),
            "tasks": list(delegation_decision.get("tasks") or []),
            "executed": bool(delegation_decision.get("executed")),
            "is_multi_domain": len(list(delegation_decision.get("selected_domains") or [])) > 1,
            "warnings": list(delegation_decision.get("warnings") or []),
        }

        delegated_response = dict(delegation_decision.get("response") or {})
        if delegated_response:
            delegated_response.setdefault("session_id", str(run_context.session_id or ""))
            orchestrator = delegated_response.get("orchestrator")
            if not isinstance(orchestrator, dict):
                orchestrator = {}
            orchestrator.setdefault("intent", str(pre_classification.get("intent") or ""))
            orchestrator.setdefault("domain", str(pre_classification.get("domain") or ""))
            orchestrator.setdefault("selected_agent", str(pre_classification.get("selected_agent") or ""))
            orchestrator.setdefault("classifier_source", "delegation_active")
            orchestrator.setdefault("needs_database", bool(pre_classification.get("needs_database")))
            orchestrator.setdefault("output_mode", "summary")
            delegated_response["orchestrator"] = orchestrator
            if "data_sources" not in delegated_response or not isinstance(delegated_response.get("data_sources"), dict):
                delegated_response["data_sources"] = {}

        if precomputed_response:
            planned_capability = dict(candidate_plans[0] if candidate_plans else bootstrap_plan)
            policy_decision = self.policy_guard.evaluate(
                run_context=run_context,
                planned_capability=planned_capability,
            )
            route = {
                "routing_mode": run_context.routing_mode,
                "selected_capability_id": str(
                    planned_capability.get("capability_id")
                    or f"query_intelligence.{str(query_intelligence.get('execution_plan', {}).get('strategy') or 'precomputed')}.v1"
                ),
                "execute_capability": False,
                "use_legacy": False,
                "shadow_enabled": True,
                "reason": f"query_intelligence_{query_intelligence_mode}_precomputed_response",
                "policy_action": policy_decision.action.value,
                "policy_allowed": policy_decision.allowed,
                "capability_exists": bool(planned_capability.get("capability_exists")),
                "rollout_enabled": bool(planned_capability.get("rollout_enabled", True)),
            }
            primary_response = precomputed_response
            run_context.metadata["proactive_loop"] = {
                "enabled": False,
                "iterations_ran": 0,
                "max_iterations": 0,
                "selected_capability_id": planned_capability.get("capability_id"),
                "used_legacy": False,
                "iterations": [],
            }
        elif delegated_response and bool(delegation_decision.get("executed")):
            planned_capability = dict(candidate_plans[0] if candidate_plans else bootstrap_plan)
            policy_decision = self.policy_guard.evaluate(
                run_context=run_context,
                planned_capability=planned_capability,
            )
            route = {
                "routing_mode": run_context.routing_mode,
                "selected_capability_id": str(planned_capability.get("capability_id") or "delegation.ausentismo.v1"),
                "execute_capability": True,
                "use_legacy": False,
                "shadow_enabled": True,
                "reason": "delegation_active_mode",
                "policy_action": policy_decision.action.value,
                "policy_allowed": policy_decision.allowed,
                "capability_exists": True,
                "rollout_enabled": True,
            }
            primary_response = delegated_response
            run_context.metadata["proactive_loop"] = {
                "enabled": False,
                "iterations_ran": 0,
                "max_iterations": 0,
                "selected_capability_id": planned_capability.get("capability_id"),
                "used_legacy": False,
                "iterations": [],
            }
        else:
            execution = self._execute_with_proactive_loop(
                message=message,
                session_id=session_id,
                reset_memory=reset_memory,
                run_context=run_context,
                planned_candidates=candidate_plans,
                legacy_runner=legacy_runner,
                observability=observability,
                memory_context=pre_memory_context,
            )
            planned_capability = dict(
                execution.get("planned_capability") or (candidate_plans[0] if candidate_plans else bootstrap_plan)
            )
            policy_decision = execution.get("policy_decision")
            route = dict(execution.get("route") or {})
            if policy_decision is None:
                policy_decision = self.policy_guard.evaluate(
                    run_context=run_context,
                    planned_capability=planned_capability,
                )
            primary_response = dict(execution.get("response") or {})
        classification = self._extract_classification(primary_response)

        divergence = self.bridge.compare(
            classification=classification,
            planned_capability=planned_capability,
        )

        # Refresh business hints using resolved capability/domain for better relevance.
        resolved_memory_context = self.memory_runtime.load_context_for_chat(
            user_key=user_key,
            domain_code=self._domain_code_from_capability(planned_capability),
            capability_id=str(planned_capability.get("capability_id") or "").strip() or None,
            run_context=run_context,
            observability=observability,
        )
        run_context.metadata["memory_context"]["resolved"] = {
            "user_memory_count": len(resolved_memory_context.get("user_memory") or []),
            "business_memory_count": len(resolved_memory_context.get("business_memory") or []),
            "domain_code": self._domain_code_from_capability(planned_capability),
            "capability_id": planned_capability.get("capability_id"),
        }

        candidates = self.memory_runtime.detect_candidates(
            message=message,
            classification=classification,
            planned_capability=planned_capability,
            legacy_response=primary_response,
            run_context=run_context,
            user_key=user_key,
            observability=observability,
        )
        memory_effects = self.memory_runtime.persist_candidates(
            user_key=user_key,
            candidates=candidates,
            run_context=run_context,
            observability=observability,
        )
        memory_effects = self._record_query_pattern_memory(
            user_key=user_key,
            run_context=run_context,
            response=primary_response,
            memory_effects=memory_effects,
            observability=observability,
        )

        self._record_shadow_observability(
            observability=observability,
            run_context=run_context,
            classification=classification,
            planned_capability=planned_capability,
            route=route,
            divergence=divergence,
        )

        return self.response_assembler.assemble(
            legacy_response=primary_response,
            run_context=run_context,
            planned_capability=planned_capability,
            route=route,
            policy_decision=policy_decision,
            divergence=divergence,
            memory_effects=memory_effects,
        )

    def _resolve_query_intelligence(
        self,
        *,
        message: str,
        base_classification: dict[str, Any],
        run_context: RunContext,
        observability,
    ) -> dict[str, Any]:
        mode = self._query_intelligence_mode()
        if mode == "off":
            run_context.metadata["query_intelligence"] = {
                "mode": mode,
                "enabled": False,
            }
            return {"mode": mode, "enabled": False}

        try:
            classification_for_qi = dict(base_classification or {})
            domain_code = str(classification_for_qi.get("domain") or "").strip().lower()
            rescued_domain = self._rescue_query_domain(
                message=message,
                domain_code=domain_code,
            )
            if rescued_domain and rescued_domain != domain_code:
                classification_for_qi["domain"] = rescued_domain
                classification_for_qi["intent"] = "empleados_query"
                classification_for_qi["selected_agent"] = "rrhh_agent"
                classification_for_qi["needs_database"] = True
                domain_code = rescued_domain
                self._record_event(
                    observability=observability,
                    event_type="query_domain_rescued",
                    source="ChatApplicationService",
                    meta={
                        "run_id": run_context.run_id,
                        "trace_id": run_context.trace_id,
                        "from_domain": str(base_classification.get("domain") or ""),
                        "to_domain": rescued_domain,
                        "reason": "rrhh_signals_detected",
                    },
                    only_if=True,
                )
            semantic_context = self.semantic_business_resolver.build_semantic_context(
                domain_code=domain_code,
                include_dictionary=True,
            )
            intent = self.query_intent_resolver.resolve(
                message=message,
                base_classification=classification_for_qi,
                semantic_context=semantic_context,
            )
            resolved_query = self.semantic_business_resolver.resolve_query(
                message=message,
                intent=intent,
                base_classification=classification_for_qi,
            )
            execution_plan = self.query_execution_planner.plan(
                run_context=run_context,
                resolved_query=resolved_query,
            )
            self._record_query_intelligence_semantic_events(
                observability=observability,
                run_context=run_context,
                resolved_query=resolved_query,
            )

            classification_override = self._build_query_intelligence_classification_override(
                resolved_query=resolved_query,
            )
            precomputed_response: dict[str, Any] = {}
            execution_result: dict[str, Any] | None = None
            if mode == "active":
                if execution_plan.strategy == "ask_context":
                    precomputed_response = self.query_execution_planner.build_missing_context_response(
                        run_context=run_context,
                        resolved_query=resolved_query,
                        execution_plan=execution_plan,
                    )
                elif execution_plan.strategy == "sql_assisted":
                    execution_result = self.query_execution_planner.execute_sql_assisted(
                        run_context=run_context,
                        resolved_query=resolved_query,
                        execution_plan=execution_plan,
                        observability=observability,
                    )
                    if bool(execution_result.get("ok")) and isinstance(execution_result.get("response"), dict):
                        candidate_response = dict(execution_result.get("response") or {})
                        validation = self.result_satisfaction_validator.validate(
                            message=message,
                            response=candidate_response,
                            resolved_query=resolved_query,
                            execution_plan=execution_plan,
                        )
                        if validation.satisfied:
                            precomputed_response = candidate_response
                        else:
                            execution_result["validation"] = validation.as_dict()

            payload = {
                "mode": mode,
                "enabled": True,
                "intent": intent.as_dict(),
                "resolved_query": resolved_query.as_dict(),
                "execution_plan": execution_plan.as_dict(),
                "classification_override": classification_override,
                "precomputed_response": precomputed_response,
                "execution_result": dict(execution_result or {}),
            }
            run_context.metadata["query_intelligence"] = payload

            self._record_event(
                observability=observability,
                event_type="query_intelligence_resolved",
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "mode": mode,
                    "domain_code": resolved_query.intent.domain_code,
                    "template_id": resolved_query.intent.template_id,
                    "strategy": execution_plan.strategy,
                    "capability_id": execution_plan.capability_id,
                    "precomputed": bool(precomputed_response),
                },
                only_if=True,
            )
            return payload
        except Exception as exc:
            run_context.metadata["query_intelligence"] = {
                "mode": mode,
                "enabled": True,
                "error": str(exc),
            }
            self._record_event(
                observability=observability,
                event_type="query_intelligence_error",
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "mode": mode,
                    "error": str(exc),
                },
                only_if=True,
            )
            return {"mode": mode, "enabled": True, "error": str(exc)}

    def _apply_query_intelligence_plan_overrides(
        self,
        *,
        candidate_plans: list[dict[str, Any]],
        fallback_plan: dict[str, Any],
        query_intelligence: dict[str, Any],
        classification: dict[str, Any],
    ) -> list[dict[str, Any]]:
        plans = [dict(item) for item in list(candidate_plans or []) if isinstance(item, dict)]
        if str(query_intelligence.get("mode") or "off") != "active":
            return plans
        execution_plan = dict(query_intelligence.get("execution_plan") or {})
        capability_id = str(execution_plan.get("capability_id") or "").strip()
        plan_constraints = dict(execution_plan.get("constraints") or {})
        if not capability_id:
            return plans
        override_mode = self._query_intelligence_plan_override_mode()
        plans = self._apply_query_constraints_to_matching_plan(
            plans=plans,
            capability_id=capability_id,
            plan_constraints=plan_constraints,
        )
        if plans:
            if override_mode == "off":
                return plans
            first_capability = str(plans[0].get("capability_id") or "").strip()
            if first_capability == capability_id:
                return plans
            if override_mode == "soft":
                if first_capability.startswith("legacy.") or first_capability.startswith("general."):
                    first = self._switch_capability(
                        current=plans[0],
                        capability_id=capability_id,
                        reason_suffix="query_intelligence_soft_override",
                    )
                    first["candidate_rank"] = 1
                    first["candidate_score"] = max(int(first.get("candidate_score") or 0), 130)
                    first["query_constraints"] = plan_constraints
                    plans[0] = first
                    return plans
                if not any(str(item.get("capability_id") or "").strip() == capability_id for item in plans):
                    injected = self._build_query_intelligence_fallback_plan(
                        capability_id=capability_id,
                        fallback_plan=fallback_plan,
                        classification=classification,
                    )
                    injected["query_constraints"] = plan_constraints
                    injected["candidate_rank"] = len(plans) + 1
                    plans.append(injected)
                return plans

            # hard override
            first = self._switch_capability(
                current=plans[0],
                capability_id=capability_id,
                reason_suffix="query_intelligence_hard_override",
            )
            first["candidate_rank"] = 1
            first["candidate_score"] = max(int(first.get("candidate_score") or 0), 130)
            first["query_constraints"] = plan_constraints
            plans[0] = first
            return plans

        plan = self._build_query_intelligence_fallback_plan(
            capability_id=capability_id,
            fallback_plan=fallback_plan,
            classification=classification,
        )
        plan["query_constraints"] = plan_constraints
        return [plan]

    @staticmethod
    def _query_intelligence_plan_override_mode() -> str:
        raw = str(os.getenv("IA_DEV_QUERY_INTELLIGENCE_PLAN_OVERRIDE_MODE", "soft") or "").strip().lower()
        if raw in {"0", "false", "off", "disabled", "none"}:
            return "off"
        if raw in {"hard", "force", "strict"}:
            return "hard"
        return "soft"

    @staticmethod
    def _apply_query_constraints_to_matching_plan(
        *,
        plans: list[dict[str, Any]],
        capability_id: str,
        plan_constraints: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not capability_id:
            return [dict(item) for item in list(plans or [])]
        updated: list[dict[str, Any]] = []
        for plan in list(plans or []):
            payload = dict(plan or {})
            if str(payload.get("capability_id") or "").strip() == capability_id and plan_constraints:
                merged = dict(payload.get("query_constraints") or {})
                merged.update(plan_constraints)
                payload["query_constraints"] = merged
                payload["candidate_score"] = max(int(payload.get("candidate_score") or 0), 125)
            updated.append(payload)
        return updated

    def _build_query_intelligence_fallback_plan(
        self,
        *,
        capability_id: str,
        fallback_plan: dict[str, Any],
        classification: dict[str, Any],
    ) -> dict[str, Any]:
        definition = self.catalog.get(capability_id)
        source = {
            "intent": str(classification.get("intent") or ""),
            "domain": str(classification.get("domain") or ""),
            "output_mode": str(classification.get("output_mode") or "summary"),
            "needs_database": bool(classification.get("needs_database", True)),
        }
        return {
            "capability_id": capability_id,
            "capability_exists": bool(definition),
            "rollout_enabled": bool(definition),
            "handler_key": definition.handler_key if definition else str(fallback_plan.get("handler_key") or "legacy.passthrough"),
            "policy_tags": list(definition.policy_tags) if definition else [],
            "legacy_intents": list(definition.legacy_intents) if definition else [],
            "reason": "query_intelligence_fallback_plan",
            "source": source,
            "dictionary_hints": dict(fallback_plan.get("dictionary_hints") or {}),
            "policy_planner_hint": {},
            "semantic_signals": {},
            "candidate_rank": 1,
            "candidate_score": 130,
            "workflow_hints": {},
        }

    @staticmethod
    def _build_query_intelligence_classification_override(
        *,
        resolved_query: ResolvedQuerySpec,
    ) -> dict[str, Any]:
        domain = str(resolved_query.intent.domain_code or "").strip().lower()
        routing_domain = domain
        if domain == "ausentismo":
            routing_domain = "attendance"
        elif domain == "transporte":
            routing_domain = "transport"
        elif domain == "rrhh":
            routing_domain = "empleados"
        output_mode = "summary"
        if resolved_query.intent.operation in {"detail", "aggregate", "trend"}:
            output_mode = "table"
        if resolved_query.intent.operation == "count":
            output_mode = "summary"
        agent = "analista_agent"
        if routing_domain in {"ausentismo", "attendance"}:
            agent = "attendance_agent"
        elif routing_domain in {"empleados", "rrhh"}:
            agent = "rrhh_agent"
        elif routing_domain in {"transporte", "transport"}:
            agent = "transport_agent"
        return {
            "intent": str(resolved_query.intent.operation or "query"),
            "domain": routing_domain,
            "selected_agent": agent,
            "classifier_source": f"query_intelligence_{resolved_query.intent.source}",
            "needs_database": routing_domain not in {"general", ""},
            "output_mode": output_mode,
            "needs_personal_join": bool("cedula" in dict(resolved_query.normalized_filters or {})),
        }

    @staticmethod
    def _query_intelligence_mode() -> str:
        enabled = str(os.getenv("IA_DEV_QUERY_INTELLIGENCE_ENABLED", "0") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if not enabled:
            return "off"
        mode = str(os.getenv("IA_DEV_QUERY_INTELLIGENCE_MODE", "shadow") or "shadow").strip().lower()
        if mode not in {"off", "shadow", "active"}:
            return "shadow"
        return mode

    @staticmethod
    def _rescue_query_domain(*, message: str, domain_code: str) -> str:
        normalized_domain = str(domain_code or "").strip().lower()
        if normalized_domain not in {"", "general"}:
            return normalized_domain
        normalized_message = ChatApplicationService._normalize_text(message)
        if ChatApplicationService._has_rrhh_domain_signals(normalized_message):
            return "empleados"
        return normalized_domain or "general"

    @staticmethod
    def _has_rrhh_domain_signals(normalized_message: str) -> bool:
        clean = str(normalized_message or "").strip().lower()
        if not clean:
            return False
        return bool(
            re.search(
                r"\b(colaborador(?:es)?|usuario(?:s)?|emplead\w*|cedula|rrhh)\b",
                clean,
            )
        )

    def _record_query_intelligence_semantic_events(
        self,
        *,
        observability,
        run_context: RunContext,
        resolved_query: ResolvedQuerySpec,
    ) -> None:
        semantic_context = dict(resolved_query.semantic_context or {})
        seed_payload = dict(semantic_context.get("dictionary_seed") or {})
        if seed_payload.get("enabled"):
            status = str(seed_payload.get("status") or "skipped").strip().lower()
            event_type = "dictionary_rrhh_synonym_seed_skipped"
            if status == "applied":
                event_type = "dictionary_rrhh_synonym_seed_applied"
            elif status == "error":
                event_type = "dictionary_rrhh_synonym_seed_error"
            self._record_event(
                observability=observability,
                event_type=event_type,
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "status": status,
                    "inserted": int(seed_payload.get("inserted") or 0),
                    "skipped": int(seed_payload.get("skipped") or 0),
                    "errors": list(seed_payload.get("errors") or []),
                },
                only_if=True,
            )

        for event in list(semantic_context.get("semantic_events") or []):
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("event_type") or "").strip()
            if not event_type:
                continue
            self._record_event(
                observability=observability,
                event_type=event_type,
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "domain_code": str(resolved_query.intent.domain_code or ""),
                    **dict(event),
                },
                only_if=True,
            )

    def _record_query_pattern_memory(
        self,
        *,
        user_key: str | None,
        run_context: RunContext,
        response: dict[str, Any],
        memory_effects: dict[str, Any],
        observability,
    ) -> dict[str, Any]:
        effects = dict(memory_effects or {})
        metadata = dict(run_context.metadata.get("query_intelligence") or {})
        hydrated = self._hydrate_query_intelligence_contracts(metadata=metadata)
        resolved_query = hydrated.get("resolved_query")
        execution_plan = hydrated.get("execution_plan")
        if resolved_query is None or execution_plan is None:
            return effects
        validation = self.result_satisfaction_validator.validate(
            message=str(resolved_query.intent.raw_query or ""),
            response=response,
            resolved_query=resolved_query,
            execution_plan=execution_plan,
        )
        metadata["final_satisfaction"] = validation.as_dict()
        run_context.metadata["query_intelligence"] = metadata

        try:
            result = self.query_pattern_memory_service.record_success(
                user_key=user_key,
                resolved_query=resolved_query,
                execution_plan=execution_plan,
                validation=validation,
                run_context=run_context,
                response=response,
                observability=observability,
            )
        except Exception as exc:
            result = {"saved": False, "reason": f"pattern_memory_error:{type(exc).__name__}"}
            self._record_event(
                observability=observability,
                event_type="query_pattern_memory_failed",
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "error_type": type(exc).__name__,
                },
                only_if=True,
            )
        metadata["pattern_memory"] = dict(result or {})
        run_context.metadata["query_intelligence"] = metadata

        if bool(result.get("saved")):
            proposal = dict((result.get("result") or {}).get("proposal") or {})
            if proposal:
                pending = list(effects.get("pending_proposals") or [])
                pending.append(proposal)
                effects["pending_proposals"] = pending
        return effects

    def _hydrate_query_intelligence_contracts(self, *, metadata: dict[str, Any]) -> dict[str, Any]:
        resolved_query_payload = metadata.get("resolved_query")
        execution_plan_payload = metadata.get("execution_plan")
        if not isinstance(resolved_query_payload, dict) or not isinstance(execution_plan_payload, dict):
            return {"resolved_query": None, "execution_plan": None}

        resolved_intent_payload = dict(resolved_query_payload.get("intent") or {})
        intent = StructuredQueryIntent(
            raw_query=str(resolved_intent_payload.get("raw_query") or ""),
            domain_code=str(resolved_intent_payload.get("domain_code") or ""),
            operation=str(resolved_intent_payload.get("operation") or ""),
            template_id=str(resolved_intent_payload.get("template_id") or ""),
            entity_type=str(resolved_intent_payload.get("entity_type") or ""),
            entity_value=str(resolved_intent_payload.get("entity_value") or ""),
            filters=dict(resolved_intent_payload.get("filters") or {}),
            period=dict(resolved_intent_payload.get("period") or {}),
            group_by=list(resolved_intent_payload.get("group_by") or []),
            metrics=list(resolved_intent_payload.get("metrics") or []),
            confidence=float(resolved_intent_payload.get("confidence") or 0.0),
            source=str(resolved_intent_payload.get("source") or "rules"),
            warnings=list(resolved_intent_payload.get("warnings") or []),
        )
        resolved_query = ResolvedQuerySpec(
            intent=intent,
            semantic_context=dict(resolved_query_payload.get("semantic_context") or {}),
            normalized_filters=dict(resolved_query_payload.get("normalized_filters") or {}),
            normalized_period=dict(resolved_query_payload.get("normalized_period") or {}),
            mapped_columns=dict(resolved_query_payload.get("mapped_columns") or {}),
            warnings=list(resolved_query_payload.get("warnings") or []),
        )
        execution_plan = QueryExecutionPlan(
            strategy=str(execution_plan_payload.get("strategy") or ""),
            reason=str(execution_plan_payload.get("reason") or ""),
            domain_code=str(execution_plan_payload.get("domain_code") or ""),
            capability_id=str(execution_plan_payload.get("capability_id") or "") or None,
            sql_query=str(execution_plan_payload.get("sql_query") or "") or None,
            requires_context=bool(execution_plan_payload.get("requires_context")),
            missing_context=list(execution_plan_payload.get("missing_context") or []),
            constraints=dict(execution_plan_payload.get("constraints") or {}),
            policy=dict(execution_plan_payload.get("policy") or {}),
            metadata=dict(execution_plan_payload.get("metadata") or {}),
        )
        return {
            "resolved_query": resolved_query,
            "execution_plan": execution_plan,
        }

    def _plan_candidates(
        self,
        *,
        message: str,
        classification: dict[str, Any],
        planning_context: dict[str, Any],
        fallback_plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        max_candidates = self._proactive_loop_max_iterations() + 1
        if hasattr(self.planner, "plan_candidates_from_legacy"):
            try:
                planned = self.planner.plan_candidates_from_legacy(
                    message=message,
                    classification=classification,
                    planning_context=planning_context,
                    max_candidates=max_candidates,
                )
            except TypeError:
                planned = self.planner.plan_candidates_from_legacy(
                    message=message,
                    classification=classification,
                )
            if planned:
                return [dict(item) for item in planned if isinstance(item, dict)]

        try:
            single = self.planner.plan_from_legacy(
                message=message,
                classification=classification,
                planning_context=planning_context,
            )
        except TypeError:
            single = self.planner.plan_from_legacy(
                message=message,
                classification=classification,
            )
        if isinstance(single, dict) and single:
            return [dict(single)]
        return [dict(fallback_plan)]

    def _execute_with_proactive_loop(
        self,
        *,
        message: str,
        session_id: str | None,
        reset_memory: bool,
        run_context: RunContext,
        planned_candidates: list[dict[str, Any]],
        legacy_runner: Callable[..., dict[str, Any]],
        observability,
        memory_context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        candidates = [dict(item) for item in planned_candidates if isinstance(item, dict)]
        if not candidates:
            candidates = [self.planner.plan_from_legacy(message=message, classification=self._bootstrap_classification(message=message))]
        query_intelligence_meta = dict(run_context.metadata.get("query_intelligence") or {})
        hydrated = self._hydrate_query_intelligence_contracts(metadata=query_intelligence_meta)
        resolved_query = hydrated.get("resolved_query")
        execution_plan = hydrated.get("execution_plan")

        loop_enabled = self._proactive_loop_enabled(run_context=run_context)
        max_iterations = self._proactive_loop_max_iterations()
        if not loop_enabled:
            max_iterations = 1

        visited_capabilities: set[str] = set()
        iteration_summaries: list[dict[str, Any]] = []

        selected_plan = dict(candidates[0])
        selected_policy = self.policy_guard.evaluate(
            run_context=run_context,
            planned_capability=selected_plan,
        )
        selected_route = self.router.route(
            run_context=run_context,
            planned_capability=selected_plan,
            policy_decision=selected_policy,
        )
        selected_execution: dict[str, Any] | None = None

        iterations_ran = 0
        for idx, plan in enumerate(candidates):
            if iterations_ran >= max_iterations:
                break
            capability_id = str(plan.get("capability_id") or "").strip()
            if capability_id and capability_id in visited_capabilities:
                continue
            if capability_id:
                visited_capabilities.add(capability_id)
            iterations_ran += 1

            policy_decision = self.policy_guard.evaluate(
                run_context=run_context,
                planned_capability=plan,
            )
            self._record_policy_decision_event(
                observability=observability,
                run_context=run_context,
                planned_capability=plan,
                policy_decision=policy_decision,
                loop_iteration=iterations_ran,
            )
            route = self.router.route(
                run_context=run_context,
                planned_capability=plan,
                policy_decision=policy_decision,
            )

            self._record_event(
                observability=observability,
                event_type="proactive_loop_iteration",
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "session_id": run_context.session_id,
                    "iteration": iterations_ran,
                    "max_iterations": max_iterations,
                    "capability_id": plan.get("capability_id"),
                    "candidate_rank": plan.get("candidate_rank"),
                    "route_reason": route.get("reason"),
                    "policy_action": policy_decision.action.value,
                },
                only_if=loop_enabled,
            )

            execution = self._execute_primary_path(
                message=message,
                session_id=session_id,
                reset_memory=reset_memory,
                run_context=run_context,
                planned_capability=plan,
                route=route,
                legacy_runner=legacy_runner,
                observability=observability,
                memory_context=memory_context,
                resolved_query=resolved_query,
                execution_plan=execution_plan,
                allow_legacy_fallback=not loop_enabled,
            )
            satisfaction = self._evaluate_result_satisfaction(
                message=message,
                planned_capability=plan,
                execution=execution,
                resolved_query=resolved_query,
                execution_plan=execution_plan,
            )
            execution["satisfied"] = bool(satisfaction.get("satisfied", True))
            execution["satisfaction_reason"] = str(satisfaction.get("reason") or "")

            iteration_summary = {
                "iteration": iterations_ran,
                "capability_id": str(plan.get("capability_id") or ""),
                "route_reason": str(route.get("reason") or ""),
                "policy_action": policy_decision.action.value,
                "ok": bool(execution.get("ok")),
                "satisfied": bool(execution.get("satisfied", True)),
                "satisfaction_reason": str(execution.get("satisfaction_reason") or ""),
                "used_legacy": bool(execution.get("used_legacy")),
                "fallback_reason": execution.get("fallback_reason"),
            }
            iteration_summaries.append(iteration_summary)

            selected_plan = dict(plan)
            selected_policy = policy_decision
            selected_route = dict(route)
            selected_execution = dict(execution or {})

            if bool(execution.get("ok")) and bool(execution.get("satisfied", True)):
                self._record_event(
                    observability=observability,
                    event_type="proactive_loop_stop",
                    source="ChatApplicationService",
                    meta={
                        "run_id": run_context.run_id,
                        "trace_id": run_context.trace_id,
                        "stop_reason": "capability_executed_and_satisfied",
                        "iteration": iterations_ran,
                        "capability_id": plan.get("capability_id"),
                    },
                    only_if=loop_enabled,
                )
                break
            if bool(execution.get("ok")) and not bool(execution.get("satisfied", True)):
                self._record_event(
                    observability=observability,
                    event_type="proactive_loop_unsatisfied_result",
                    source="ChatApplicationService",
                    meta={
                        "run_id": run_context.run_id,
                        "trace_id": run_context.trace_id,
                        "iteration": iterations_ran,
                        "capability_id": plan.get("capability_id"),
                        "reason": execution.get("satisfaction_reason"),
                    },
                    only_if=loop_enabled,
                )

        if selected_execution is None:
            selected_execution = self._execute_primary_path(
                message=message,
                session_id=session_id,
                reset_memory=reset_memory,
                run_context=run_context,
                planned_capability=selected_plan,
                route=selected_route,
                legacy_runner=legacy_runner,
                observability=observability,
                memory_context=memory_context,
                resolved_query=resolved_query,
                execution_plan=execution_plan,
                allow_legacy_fallback=True,
            )

        if loop_enabled and not bool(selected_execution.get("ok")):
            # Safe fallback to legacy with first candidate context.
            legacy_route = dict(selected_route or {})
            legacy_route["execute_capability"] = False
            legacy_route["use_legacy"] = True
            legacy_route["reason"] = "proactive_loop_exhausted_all_candidates"
            selected_execution = self._execute_primary_path(
                message=message,
                session_id=session_id,
                reset_memory=reset_memory,
                run_context=run_context,
                planned_capability=selected_plan,
                route=legacy_route,
                legacy_runner=legacy_runner,
                observability=observability,
                memory_context=memory_context,
                resolved_query=resolved_query,
                execution_plan=execution_plan,
                allow_legacy_fallback=True,
            )
            selected_route = legacy_route
            self._record_event(
                observability=observability,
                event_type="proactive_loop_fallback_legacy",
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "iterations": iterations_ran,
                    "capability_id": selected_plan.get("capability_id"),
                    "route_reason": selected_route.get("reason"),
                },
            )

        run_context.metadata["proactive_loop"] = {
            "enabled": loop_enabled,
            "iterations_ran": iterations_ran,
            "max_iterations": max_iterations,
            "selected_capability_id": selected_plan.get("capability_id"),
            "used_legacy": bool(selected_execution.get("used_legacy")),
            "satisfied": bool(selected_execution.get("satisfied", True)),
            "satisfaction_reason": str(selected_execution.get("satisfaction_reason") or ""),
            "iterations": iteration_summaries,
        }

        return {
            "response": dict(selected_execution.get("response") or {}),
            "planned_capability": selected_plan,
            "policy_decision": selected_policy,
            "route": selected_route,
            "execution_meta": selected_execution,
        }

    def _execute_primary_path(
        self,
        *,
        message: str,
        session_id: str | None,
        reset_memory: bool,
        run_context: RunContext,
        planned_capability: dict[str, Any],
        route: dict[str, Any],
        legacy_runner: Callable[..., dict[str, Any]],
        observability,
        memory_context: dict[str, Any] | None,
        resolved_query: ResolvedQuerySpec | None = None,
        execution_plan: QueryExecutionPlan | None = None,
        allow_legacy_fallback: bool = True,
    ) -> dict[str, Any]:
        capability_id = str(planned_capability.get("capability_id") or "")
        plan_constraints = dict(planned_capability.get("query_constraints") or {})
        runtime_execution_plan = execution_plan
        if runtime_execution_plan is None and plan_constraints:
            runtime_execution_plan = QueryExecutionPlan(
                strategy="capability",
                reason="planned_capability_query_constraints",
                domain_code=self._domain_code_from_capability(planned_capability) or "",
                capability_id=capability_id or None,
                constraints=plan_constraints,
            )
        elif runtime_execution_plan is not None and plan_constraints and not dict(runtime_execution_plan.constraints or {}):
            runtime_execution_plan.constraints = plan_constraints
        capability_domain = capability_id.split(".", 1)[0] if "." in capability_id else ""
        is_domain_capability = capability_domain in {"attendance", "transport", "empleados"}
        selected_event_type = f"{capability_domain}_capability_selected"
        executed_event_type = f"{capability_domain}_handler_executed"
        fallback_event_type = f"{capability_domain}_fallback_legacy"

        if bool(route.get("execute_capability")):
            self._record_event(
                observability=observability,
                event_type=selected_event_type,
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "session_id": run_context.session_id,
                    "capability_id": capability_id,
                    "capability_domain": capability_domain,
                    "route_reason": route.get("reason"),
                },
                only_if=is_domain_capability,
            )
            capability_result = self.router.execute(
                run_context=run_context,
                route=route,
                planned_capability=planned_capability,
                message=message,
                session_id=session_id,
                reset_memory=reset_memory,
                memory_context=memory_context,
                resolved_query=resolved_query,
                execution_plan=runtime_execution_plan,
                observability=observability,
            )
            if capability_result.get("ok") and isinstance(capability_result.get("response"), dict):
                self._record_event(
                    observability=observability,
                    event_type=executed_event_type,
                    source="ChatApplicationService",
                    meta={
                        "run_id": run_context.run_id,
                        "trace_id": run_context.trace_id,
                        "session_id": run_context.session_id,
                        "capability_id": capability_id,
                        "capability_domain": capability_domain,
                        "route_reason": route.get("reason"),
                        "meta": dict(capability_result.get("meta") or {}),
                    },
                    only_if=is_domain_capability,
                )
                return {
                    "response": dict(capability_result.get("response") or {}),
                    "executed_capability": True,
                    "ok": True,
                    "used_legacy": False,
                    "fallback_reason": None,
                }

            fallback_reason = str(capability_result.get("error") or "capability_handler_failed")
            self._record_event(
                observability=observability,
                event_type=fallback_event_type,
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "session_id": run_context.session_id,
                    "capability_id": capability_id,
                    "capability_domain": capability_domain,
                    "fallback_reason": fallback_reason,
                },
                only_if=is_domain_capability,
            )
            if not allow_legacy_fallback:
                return {
                    "response": {},
                    "executed_capability": True,
                    "ok": False,
                    "used_legacy": False,
                    "fallback_reason": fallback_reason,
                }

        elif run_context.is_capability_mode_requested and is_domain_capability:
            self._record_event(
                observability=observability,
                event_type=fallback_event_type,
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "session_id": run_context.session_id,
                    "capability_id": capability_id,
                    "capability_domain": capability_domain,
                    "fallback_reason": str(route.get("reason") or "route_use_legacy"),
                },
            )
            if not allow_legacy_fallback:
                return {
                    "response": {},
                    "executed_capability": False,
                    "ok": False,
                    "used_legacy": False,
                    "fallback_reason": str(route.get("reason") or "route_use_legacy"),
                }

        if not allow_legacy_fallback:
            return {
                "response": {},
                "executed_capability": False,
                "ok": False,
                "used_legacy": False,
                "fallback_reason": str(route.get("reason") or "route_use_legacy"),
            }

        legacy_response = legacy_runner(
            message=message,
            session_id=session_id,
            reset_memory=reset_memory,
        )
        return {
            "response": dict(legacy_response or {}),
            "executed_capability": False,
            "ok": True,
            "used_legacy": True,
            "fallback_reason": str(route.get("reason") or "legacy_runner"),
        }

    def _apply_attendance_memory_hints(
        self,
        *,
        message: str,
        planned_capability: dict[str, Any],
        memory_context: dict[str, Any],
        run_context: RunContext,
        observability,
    ) -> dict[str, Any]:
        capability_id = str(planned_capability.get("capability_id") or "")
        if not capability_id.startswith("attendance."):
            return planned_capability

        hints = self._extract_memory_hints(memory_context)
        updated = dict(planned_capability)
        used_hints: list[dict[str, Any]] = []

        preferred_view = str(hints.get("recurrence_view") or hints.get("output_mode") or "").strip().lower()
        if capability_id == "attendance.recurrence.grouped.v1":
            if preferred_view == "itemized" and not self._message_wants_grouped(message):
                updated = self._switch_capability(
                    current=updated,
                    capability_id="attendance.recurrence.itemized.v1",
                    reason_suffix="memory_hint_itemized",
                )
                used_hints.append(
                    {
                        "memory_key": "attendance.recurrence.default_view",
                        "memory_value": "itemized",
                        "reason": "planner_switched_to_itemized_from_memory_hint",
                    }
                )
        elif capability_id == "attendance.recurrence.itemized.v1":
            if preferred_view in {"grouped", "summary"} and not self._message_wants_itemized(message):
                updated = self._switch_capability(
                    current=updated,
                    capability_id="attendance.recurrence.grouped.v1",
                    reason_suffix="memory_hint_grouped",
                )
                used_hints.append(
                    {
                        "memory_key": "attendance.recurrence.default_view",
                        "memory_value": preferred_view,
                        "reason": "planner_switched_to_grouped_from_memory_hint",
                    }
                )

        memory_meta = run_context.metadata.get("memory_context")
        if isinstance(memory_meta, dict):
            memory_meta["hints"] = hints
            memory_meta["hints_used"] = used_hints

        for hint in used_hints:
            self._record_event(
                observability=observability,
                event_type="attendance_memory_hint_used",
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "capability_id": updated.get("capability_id"),
                    "memory_key": hint.get("memory_key"),
                    "memory_value": hint.get("memory_value"),
                    "reason": hint.get("reason"),
                },
            )

        if hints:
            updated["memory_hints"] = hints
        return updated

    def _switch_capability(
        self,
        *,
        current: dict[str, Any],
        capability_id: str,
        reason_suffix: str,
    ) -> dict[str, Any]:
        switched = dict(current)
        definition = self.catalog.get(capability_id)
        switched["capability_id"] = capability_id
        switched["capability_exists"] = bool(definition)
        if definition is not None:
            switched["handler_key"] = definition.handler_key
            switched["policy_tags"] = list(definition.policy_tags)
            switched["legacy_intents"] = list(definition.legacy_intents)
        switched["reason"] = f"{str(current.get('reason') or 'planned')}|{reason_suffix}"
        return switched

    @staticmethod
    def _extract_memory_hints(memory_context: dict[str, Any]) -> dict[str, Any]:
        user_memory = list(memory_context.get("user_memory") or [])
        business_memory = list(memory_context.get("business_memory") or [])

        hints: dict[str, Any] = {}
        for row in user_memory:
            key = str(row.get("memory_key") or "").strip().lower()
            value = ChatApplicationService._memory_value_to_text(row.get("memory_value"))
            if key == "attendance.output_mode" and value:
                hints["output_mode"] = value
            elif key == "attendance.personal_status" and value:
                hints["personal_status"] = value
            elif key == "attendance.team" and value:
                hints["team"] = value
            elif key == "attendance.supervisor" and value:
                hints["supervisor"] = value
            elif key == "attendance.analytics.chart_type" and value:
                hints["analytics_chart_type"] = value
            elif key == "attendance.analytics.top_n" and value:
                hints["analytics_top_n"] = value
            elif key == "transport.default_period_label" and value:
                hints["transport_default_period_label"] = value
            elif key == "transport.output_mode" and value:
                hints["transport_output_mode"] = value

        for row in business_memory:
            key = str(row.get("memory_key") or "").strip().lower()
            value = ChatApplicationService._memory_value_to_text(row.get("memory_value"))
            if key == "attendance.recurrence.default_view" and value:
                hints["recurrence_view"] = value
            elif key == "attendance.default.personal_status" and value and not hints.get("personal_status"):
                hints["personal_status"] = value
            elif key == "attendance.analytics.default_chart_type" and value and not hints.get("analytics_chart_type"):
                hints["analytics_chart_type"] = value

        return hints

    @staticmethod
    def _memory_value_to_text(value: Any) -> str | None:
        raw = value
        if isinstance(value, dict):
            if "value" in value:
                raw = value.get("value")
            elif value:
                raw = next(iter(value.values()))
        text = str(raw or "").strip().lower()
        return text or None

    @staticmethod
    def _message_wants_grouped(message: str) -> bool:
        normalized = str(message or "").strip().lower()
        return any(token in normalized for token in ("agrupado", "por empleado", "resumen"))

    @staticmethod
    def _message_wants_itemized(message: str) -> bool:
        normalized = str(message or "").strip().lower()
        return any(
            token in normalized
            for token in ("dia a dia", "detalle", "itemizado", "por ausentismo", "fecha por fecha")
        )

    @staticmethod
    def _bootstrap_classification(
        *,
        message: str,
        session_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized = ChatApplicationService._normalize_text(message)
        context = dict(session_context or {})
        last_domain = str(context.get("last_domain") or "").strip().lower()
        last_needs_db = bool(context.get("last_needs_database"))
        if (
            last_domain == "attendance"
            and last_needs_db
            and ChatApplicationService._is_chart_request(normalized)
        ):
            return {
                "intent": "attendance_query",
                "domain": "attendance",
                "selected_agent": "attendance_agent",
                "classifier_source": "bootstrap_context_followup",
                "needs_database": True,
                "output_mode": "summary",
                "needs_personal_join": bool(context.get("last_output_mode") == "table"),
                "contextual_reference": ChatApplicationService._is_contextual_reference_request(normalized),
                "last_group_dimension_key": str(context.get("last_group_dimension_key") or "").strip().lower(),
                "last_group_dimension_label": str(context.get("last_group_dimension_label") or "").strip(),
                "last_aggregation_focus": str(context.get("last_aggregation_focus") or "").strip().lower(),
                "last_metric_key": str(context.get("last_metric_key") or "").strip().lower(),
                "used_tools": [],
                "dictionary_context": {},
            }
        if any(token in normalized for token in ("ausent", "asistenc", "injustificad")):
            intent = "attendance_recurrence" if "reincid" in normalized else "attendance_query"
            wants_table = any(token in normalized for token in ("tabla", "detalle", "lista", "mostrar"))
            wants_count = any(token in normalized for token in ("cantidad", "cuantos", "cuantas", "total", "resumen"))
            wants_group = any(
                token in normalized
                for token in (
                    "por supervisor",
                    "por area",
                    "por cargo",
                    "por carpeta",
                    "por justificacion",
                    "por causa",
                    "por tipo",
                    "por estado",
                )
            )
            output_mode = "table" if wants_table and not (wants_count and wants_group) else "summary"
            needs_personal_join = any(
                token in normalized
                for token in ("empleado", "personal", "supervisor", "area", "cargo", "nombre", "apellido")
            ) or intent == "attendance_recurrence"
            return {
                "intent": intent,
                "domain": "attendance",
                "selected_agent": "attendance_agent",
                "classifier_source": "bootstrap_rules",
                "needs_database": True,
                "output_mode": output_mode,
                "needs_personal_join": needs_personal_join,
                "used_tools": [],
                "dictionary_context": {},
            }
        if ChatApplicationService._has_rrhh_domain_signals(normalized):
            return {
                "intent": "empleados_query",
                "domain": "empleados",
                "selected_agent": "rrhh_agent",
                "classifier_source": "bootstrap_rules",
                "needs_database": True,
                "output_mode": "summary" if any(
                    token in normalized for token in ("cantidad", "cuantos", "cuantas", "total", "numero")
                ) else "table",
                "needs_personal_join": False,
                "used_tools": [],
                "dictionary_context": {},
            }
        if any(token in normalized for token in ("transporte", "ruta", "movilidad", "vehicul", "salieron", "salidas")):
            return {
                "intent": "transport_query",
                "domain": "transport",
                "selected_agent": "transport_agent",
                "classifier_source": "bootstrap_rules",
                "needs_database": True,
                "output_mode": "summary",
                "needs_personal_join": False,
                "used_tools": [],
                "dictionary_context": {},
            }
        if any(token in normalized for token in ("regla", "propuesta", "knowledge", "gobernanza")):
            return {
                "intent": "knowledge_change_request",
                "domain": "knowledge",
                "selected_agent": "analista_agent",
                "classifier_source": "bootstrap_rules",
                "needs_database": False,
                "output_mode": "summary",
                "used_tools": [],
                "dictionary_context": {},
            }
        return {
            "intent": "general_question",
            "domain": "general",
            "selected_agent": "analista_agent",
            "classifier_source": "bootstrap_rules",
            "needs_database": False,
            "output_mode": "summary",
            "used_tools": [],
            "dictionary_context": {},
        }

    @staticmethod
    def _is_chart_request(normalized_message: str) -> bool:
        return any(
            token in normalized_message
            for token in (
                "grafica",
                "grafico",
                "graficar",
                "chart",
                "linea",
                "barra",
                "barras",
                "visual",
                "visualizar",
            )
        )

    @staticmethod
    def _is_contextual_reference_request(normalized_message: str) -> bool:
        return any(
            token in normalized_message
            for token in (
                "reporte",
                "resultado",
                "consulta",
                "este reporte",
                "este resultado",
                "esta consulta",
                "ese reporte",
                "ese resultado",
                "informacion anterior",
                "info anterior",
                "lo anterior",
                "mismo periodo",
                "mismo rango",
                "ese periodo",
                "ese rango",
            )
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = str(text or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    @staticmethod
    def _resolve_user_key(*, actor_user_key: str | None, run_context: RunContext) -> str | None:
        explicit = str(actor_user_key or "").strip()
        if explicit:
            return explicit
        if run_context.session_id:
            return f"session:{run_context.session_id}"
        return None

    @staticmethod
    def _domain_code_from_capability(planned_capability: dict[str, Any]) -> str | None:
        capability_id = str(planned_capability.get("capability_id") or "").strip()
        if not capability_id:
            return None
        return capability_id.split(".", 1)[0].upper()

    @staticmethod
    def _extract_classification(response: dict[str, Any]) -> dict[str, Any]:
        orchestrator = dict((response or {}).get("orchestrator") or {})
        data_sources = dict((response or {}).get("data_sources") or {})
        ai_dictionary = dict(data_sources.get("ai_dictionary") or {})
        dictionary_context = ai_dictionary.get("context")
        if not isinstance(dictionary_context, dict):
            dictionary_context = {}
        return {
            "intent": str(orchestrator.get("intent") or ""),
            "domain": str(orchestrator.get("domain") or ""),
            "selected_agent": str(orchestrator.get("selected_agent") or ""),
            "classifier_source": str(orchestrator.get("classifier_source") or ""),
            "needs_database": bool(orchestrator.get("needs_database")),
            "output_mode": str(orchestrator.get("output_mode") or "summary"),
            "used_tools": list(orchestrator.get("used_tools") or []),
            "dictionary_context": dictionary_context,
        }

    def _evaluate_result_satisfaction(
        self,
        *,
        message: str,
        planned_capability: dict[str, Any],
        execution: dict[str, Any],
        resolved_query: ResolvedQuerySpec | None = None,
        execution_plan: QueryExecutionPlan | None = None,
    ) -> dict[str, Any]:
        if not bool(execution.get("ok")):
            return {"satisfied": False, "reason": "execution_not_ok"}
        validation_enabled = str(
            os.getenv("IA_DEV_QUERY_SATISFACTION_VALIDATION_ENABLED", "1") or "1"
        ).strip().lower() in {"1", "true", "yes", "on"}
        if not validation_enabled:
            return {"satisfied": True, "reason": "validation_disabled_by_flag", "checks": {}}
        response = dict(execution.get("response") or {})
        validation = self.result_satisfaction_validator.validate(
            message=message,
            response=response,
            resolved_query=resolved_query,
            execution_plan=execution_plan,
        )
        return validation.as_dict()

    @staticmethod
    def _extract_cedula_from_message(message: str) -> str | None:
        match = re.search(r"\b\d{6,13}\b", str(message or ""))
        if not match:
            return None
        return ChatApplicationService._normalize_digits(match.group(0)) or None

    @staticmethod
    def _normalize_digits(value: str) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    @staticmethod
    def _extract_period_from_response(*, response: dict[str, Any]) -> tuple[Any, Any] | None:
        candidates = []
        data = dict(response.get("data") or {})
        table = dict(data.get("table") or {})
        rows = list(table.get("rows") or [])
        if rows and isinstance(rows[0], dict):
            first = rows[0]
            # Opcional futuro: periodo en filas.
            if first.get("periodo_inicio") and first.get("periodo_fin"):
                candidates.append((str(first.get("periodo_inicio")), str(first.get("periodo_fin"))))

        reply = str(response.get("reply") or "")
        m = re.search(r"periodo\s+(\d{4}-\d{2}-\d{2})\s+al\s+(\d{4}-\d{2}-\d{2})", reply.lower())
        if m:
            candidates.append((m.group(1), m.group(2)))

        for start_text, end_text in candidates:
            try:
                from datetime import date
                return date.fromisoformat(start_text), date.fromisoformat(end_text)
            except Exception:
                continue
        return None

    def _record_policy_decision_event(
        self,
        *,
        observability,
        run_context: RunContext,
        planned_capability: dict[str, Any],
        policy_decision,
        loop_iteration: int | None = None,
    ) -> None:
        self._record_event(
            observability=observability,
            event_type="policy_runtime_decision",
            source="ChatApplicationService",
            meta={
                "run_id": run_context.run_id,
                "trace_id": run_context.trace_id,
                "session_id": run_context.session_id,
                "capability_id": planned_capability.get("capability_id"),
                "policy_action": policy_decision.action.value,
                "policy_id": policy_decision.policy_id,
                "policy_reason": policy_decision.reason,
                "policy_metadata": dict(policy_decision.metadata or {}),
                "loop_iteration": loop_iteration,
            },
        )

    @staticmethod
    def _proactive_loop_enabled(*, run_context: RunContext) -> bool:
        if not run_context.is_capability_mode_requested:
            return False
        value = str(os.getenv("IA_DEV_PROACTIVE_LOOP_ENABLED", "0") or "").strip().lower()
        return value in {"1", "true", "yes", "on"}

    @staticmethod
    def _proactive_loop_max_iterations() -> int:
        raw = str(os.getenv("IA_DEV_PROACTIVE_LOOP_MAX_ITERATIONS", "2") or "2").strip()
        try:
            value = int(raw)
        except ValueError:
            value = 2
        return max(1, min(value, 5))

    def _load_workflow_hints(self, *, user_key: str | None) -> dict[str, Any]:
        if not user_key:
            return {"pending_count": 0}
        try:
            writer = getattr(getattr(self.memory_runtime, "router", None), "writer", None)
            workflow = getattr(writer, "workflow_state", None)
            if workflow is None or not hasattr(workflow, "list_proposal_workflows"):
                return {"pending_count": 0}
            pending = workflow.list_proposal_workflows(status="pending", limit=20)
            user_pending = [
                item for item in list(pending or [])
                if str((item or {}).get("actor_user_key") or "").strip() in {"", user_key}
            ]
            return {
                "pending_count": len(user_pending),
            }
        except Exception:
            logger.exception("No se pudieron cargar workflow hints para planner")
            return {"pending_count": 0}

    @staticmethod
    def _record_event(
        *,
        observability,
        event_type: str,
        source: str,
        meta: dict[str, Any],
        only_if: bool = True,
    ) -> None:
        if not only_if:
            return
        if observability is None or not hasattr(observability, "record_event"):
            return
        try:
            observability.record_event(
                event_type=event_type,
                source=source,
                meta=meta,
            )
        except Exception:
            logger.exception("No se pudo registrar evento de observabilidad")

    @staticmethod
    def _record_shadow_observability(
        *,
        observability,
        run_context: RunContext,
        classification: dict[str, Any],
        planned_capability: dict[str, Any],
        route: dict[str, Any],
        divergence: dict[str, Any],
    ) -> None:
        if run_context.routing_mode == "intent":
            return
        if observability is None or not hasattr(observability, "record_event"):
            return
        try:
            observability.record_event(
                event_type="capability_shadow_divergence",
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "routing_mode": run_context.routing_mode,
                    "legacy_intent": classification.get("intent"),
                    "legacy_domain": classification.get("domain"),
                    "planned_capability_id": planned_capability.get("capability_id"),
                    "planned_reason": planned_capability.get("reason"),
                    "route_reason": route.get("reason"),
                    "execute_capability": bool(route.get("execute_capability")),
                    "diverged": bool(divergence.get("diverged")),
                    "divergence_reason": divergence.get("reason"),
                },
            )
        except Exception:
            logger.exception("No se pudo registrar observabilidad de capability shadow")
