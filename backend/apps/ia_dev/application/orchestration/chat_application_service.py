from __future__ import annotations

import logging
from typing import Any, Callable

from apps.ia_dev.application.context.run_context import RunContext
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
    ):
        self.catalog = catalog or CapabilityCatalog()
        self.bridge = bridge or IntentToCapabilityBridge()
        self.planner = planner or CapabilityPlanner(catalog=self.catalog, bridge=self.bridge)
        self.router = router or CapabilityRouter()
        self.policy_guard = policy_guard or PolicyGuard()
        self.response_assembler = response_assembler or LegacyResponseAssembler()

    def run(
        self,
        *,
        message: str,
        session_id: str | None,
        reset_memory: bool,
        legacy_runner: Callable[..., dict[str, Any]],
        observability=None,
    ) -> dict[str, Any]:
        run_context = RunContext.create(
            message=message,
            session_id=session_id,
            reset_memory=reset_memory,
        )

        legacy_response = legacy_runner(
            message=message,
            session_id=session_id,
            reset_memory=reset_memory,
        )
        classification = self._extract_classification(legacy_response)
        planned_capability = self.planner.plan_from_legacy(
            message=message,
            classification=classification,
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
        divergence = self.bridge.compare(
            classification=classification,
            planned_capability=planned_capability,
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
            legacy_response=legacy_response,
            run_context=run_context,
            planned_capability=planned_capability,
            route=route,
            policy_decision=policy_decision,
            divergence=divergence,
        )

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
                    "diverged": bool(divergence.get("diverged")),
                    "divergence_reason": divergence.get("reason"),
                },
            )
        except Exception:
            logger.exception("No se pudo registrar observabilidad de capability shadow")
