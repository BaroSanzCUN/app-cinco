from __future__ import annotations

import logging
from typing import Any, Callable

from apps.ia_dev.application.context.run_context import RunContext
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
    ):
        self.catalog = catalog or CapabilityCatalog()
        self.bridge = bridge or IntentToCapabilityBridge()
        self.planner = planner or CapabilityPlanner(catalog=self.catalog, bridge=self.bridge)
        self.router = router or CapabilityRouter()
        self.policy_guard = policy_guard or PolicyGuard()
        self.response_assembler = response_assembler or LegacyResponseAssembler()
        self.memory_runtime = memory_runtime or ChatMemoryRuntimeService()

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
        user_key = self._resolve_user_key(actor_user_key=actor_user_key, run_context=run_context)

        pre_classification = self._bootstrap_classification(message=message)
        planned_capability = self.planner.plan_from_legacy(
            message=message,
            classification=pre_classification,
        )
        pre_memory_context = self.memory_runtime.load_context_for_chat(
            user_key=user_key,
            domain_code=self._domain_code_from_capability(planned_capability),
            capability_id=str(planned_capability.get("capability_id") or "").strip() or None,
            run_context=run_context,
            observability=observability,
        )
        run_context.metadata["memory_context"] = {
            "user_key": user_key,
            "flags": dict(pre_memory_context.get("flags") or {}),
            "preloaded": {
                "user_memory_count": len(pre_memory_context.get("user_memory") or []),
                "business_memory_count": len(pre_memory_context.get("business_memory") or []),
                "domain_code": self._domain_code_from_capability(planned_capability),
                "capability_id": planned_capability.get("capability_id"),
            },
        }

        planned_capability = self._apply_attendance_memory_hints(
            message=message,
            planned_capability=planned_capability,
            memory_context=pre_memory_context,
            run_context=run_context,
            observability=observability,
        )

        policy_decision = self.policy_guard.evaluate(
            run_context=run_context,
            planned_capability=planned_capability,
        )
        route = self.router.route(
            run_context=run_context,
            planned_capability=planned_capability,
            policy_decision=policy_decision,
        )

        execution = self._execute_primary_path(
            message=message,
            session_id=session_id,
            reset_memory=reset_memory,
            run_context=run_context,
            planned_capability=planned_capability,
            route=route,
            legacy_runner=legacy_runner,
            observability=observability,
            memory_context=pre_memory_context,
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
    ) -> dict[str, Any]:
        capability_id = str(planned_capability.get("capability_id") or "")
        is_attendance_capability = capability_id.startswith("attendance.")

        if bool(route.get("execute_capability")):
            self._record_event(
                observability=observability,
                event_type="attendance_capability_selected",
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "session_id": run_context.session_id,
                    "capability_id": capability_id,
                    "route_reason": route.get("reason"),
                },
                only_if=is_attendance_capability,
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
                    event_type="attendance_handler_executed",
                    source="ChatApplicationService",
                    meta={
                        "run_id": run_context.run_id,
                        "trace_id": run_context.trace_id,
                        "session_id": run_context.session_id,
                        "capability_id": capability_id,
                        "route_reason": route.get("reason"),
                        "meta": dict(capability_result.get("meta") or {}),
                    },
                    only_if=is_attendance_capability,
                )
                return {
                    "response": dict(capability_result.get("response") or {}),
                    "executed_capability": True,
                }

            fallback_reason = str(capability_result.get("error") or "capability_handler_failed")
            self._record_event(
                observability=observability,
                event_type="attendance_fallback_legacy",
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "session_id": run_context.session_id,
                    "capability_id": capability_id,
                    "fallback_reason": fallback_reason,
                },
                only_if=is_attendance_capability,
            )

        elif run_context.is_capability_mode_requested and is_attendance_capability:
            self._record_event(
                observability=observability,
                event_type="attendance_fallback_legacy",
                source="ChatApplicationService",
                meta={
                    "run_id": run_context.run_id,
                    "trace_id": run_context.trace_id,
                    "session_id": run_context.session_id,
                    "capability_id": capability_id,
                    "fallback_reason": str(route.get("reason") or "route_use_legacy"),
                },
            )

        legacy_response = legacy_runner(
            message=message,
            session_id=session_id,
            reset_memory=reset_memory,
        )
        return {
            "response": dict(legacy_response or {}),
            "executed_capability": False,
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

        for row in business_memory:
            key = str(row.get("memory_key") or "").strip().lower()
            value = ChatApplicationService._memory_value_to_text(row.get("memory_value"))
            if key == "attendance.recurrence.default_view" and value:
                hints["recurrence_view"] = value
            elif key == "attendance.default.personal_status" and value and not hints.get("personal_status"):
                hints["personal_status"] = value

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
    def _bootstrap_classification(*, message: str) -> dict[str, Any]:
        normalized = str(message or "").strip().lower()
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
