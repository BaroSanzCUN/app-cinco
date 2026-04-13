from __future__ import annotations

import logging
import os
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
from apps.ia_dev.application.policies.policy_guard import PolicyGuard
from apps.ia_dev.application.routing.capability_catalog import CapabilityCatalog
from apps.ia_dev.application.routing.capability_planner import CapabilityPlanner
from apps.ia_dev.application.routing.capability_router import CapabilityRouter
from apps.ia_dev.application.routing.intent_to_capability_bridge import (
    IntentToCapabilityBridge,
)
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
    ):
        self.catalog = catalog or CapabilityCatalog()
        self.bridge = bridge or IntentToCapabilityBridge()
        self.planner = planner or CapabilityPlanner(catalog=self.catalog, bridge=self.bridge)
        self.router = router or CapabilityRouter()
        self.policy_guard = policy_guard or PolicyGuard()
        self.response_assembler = response_assembler or LegacyResponseAssembler()
        self.memory_runtime = memory_runtime or ChatMemoryRuntimeService()
        self.delegation_coordinator = delegation_coordinator or DelegationCoordinator()

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
        run_context.metadata["planned_candidates"] = [
            {
                "capability_id": str(item.get("capability_id") or ""),
                "reason": str(item.get("reason") or ""),
                "candidate_rank": int(item.get("candidate_rank") or 0),
                "candidate_score": int(item.get("candidate_score") or 0),
            }
            for item in candidate_plans
        ]

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

        if delegated_response and bool(delegation_decision.get("executed")):
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
                allow_legacy_fallback=not loop_enabled,
            )

            iteration_summary = {
                "iteration": iterations_ran,
                "capability_id": str(plan.get("capability_id") or ""),
                "route_reason": str(route.get("reason") or ""),
                "policy_action": policy_decision.action.value,
                "ok": bool(execution.get("ok")),
                "used_legacy": bool(execution.get("used_legacy")),
                "fallback_reason": execution.get("fallback_reason"),
            }
            iteration_summaries.append(iteration_summary)

            selected_plan = dict(plan)
            selected_policy = policy_decision
            selected_route = dict(route)
            selected_execution = dict(execution or {})

            if bool(execution.get("ok")):
                self._record_event(
                    observability=observability,
                    event_type="proactive_loop_stop",
                    source="ChatApplicationService",
                    meta={
                        "run_id": run_context.run_id,
                        "trace_id": run_context.trace_id,
                        "stop_reason": "capability_executed",
                        "iteration": iterations_ran,
                        "capability_id": plan.get("capability_id"),
                    },
                    only_if=loop_enabled,
                )
                break

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
                allow_legacy_fallback=True,
            )

        if loop_enabled and not bool(selected_execution.get("ok")):
            # Safe fallback to legacy with first candidate context.
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
                allow_legacy_fallback=True,
            )
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
        allow_legacy_fallback: bool = True,
    ) -> dict[str, Any]:
        capability_id = str(planned_capability.get("capability_id") or "")
        capability_domain = capability_id.split(".", 1)[0] if "." in capability_id else ""
        is_domain_capability = capability_domain in {"attendance", "transport"}
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
        normalized = str(message or "").strip().lower()
        normalized_no_accents = ChatApplicationService._normalize_text(normalized)
        context = dict(session_context or {})
        last_domain = str(context.get("last_domain") or "").strip().lower()
        last_needs_db = bool(context.get("last_needs_database"))
        if (
            last_domain == "attendance"
            and last_needs_db
            and ChatApplicationService._is_chart_request(normalized_no_accents)
        ):
            return {
                "intent": "attendance_query",
                "domain": "attendance",
                "selected_agent": "attendance_agent",
                "classifier_source": "bootstrap_context_followup",
                "needs_database": True,
                "output_mode": "summary",
                "needs_personal_join": bool(context.get("last_output_mode") == "table"),
                "used_tools": [],
                "dictionary_context": {},
            }
        if any(token in normalized for token in ("ausent", "asistenc", "injustificad", "rrhh")):
            intent = "attendance_recurrence" if "reincid" in normalized else "attendance_query"
            output_mode = "summary" if "resumen" in normalized and "tabla" not in normalized else "table"
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
