from __future__ import annotations

from typing import Any

from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.application.policies.policy_guard import PolicyAction, PolicyDecision
from apps.ia_dev.domains.attendance.handler import AttendanceHandler
from apps.ia_dev.domains.transport.handler import TransportHandler


class CapabilityRouter:
    """
    Router incremental:
    - intent mode: legacy only
    - capability_shadow: legacy + trazas de capacidad
    - capability mode: ejecuta attendance/transport capability-first con fallback seguro
    """

    def __init__(
        self,
        *,
        attendance_handler: AttendanceHandler | None = None,
        transport_handler: TransportHandler | None = None,
    ):
        self._attendance_handler = attendance_handler
        self._transport_handler = transport_handler

    def route(
        self,
        *,
        run_context: RunContext,
        planned_capability: dict[str, Any],
        policy_decision: PolicyDecision,
    ) -> dict[str, Any]:
        capability_id = str(planned_capability.get("capability_id") or "legacy.passthrough.v1")
        routing_mode = run_context.routing_mode
        capability_exists = bool(planned_capability.get("capability_exists"))
        rollout_enabled = bool(planned_capability.get("rollout_enabled", True))
        capability_domain = capability_id.split(".", 1)[0] if "." in capability_id else "legacy"
        policy_allows = policy_decision.action == PolicyAction.ALLOW

        if routing_mode == "intent":
            return {
                "routing_mode": routing_mode,
                "selected_capability_id": capability_id,
                "execute_capability": False,
                "use_legacy": True,
                "shadow_enabled": False,
                "reason": "intent_mode_keeps_legacy_path",
                "policy_action": policy_decision.action.value,
                "policy_allowed": policy_allows,
                "capability_exists": capability_exists,
                "rollout_enabled": rollout_enabled,
            }

        if routing_mode == "capability_shadow":
            return {
                "routing_mode": routing_mode,
                "selected_capability_id": capability_id,
                "execute_capability": False,
                "use_legacy": True,
                "shadow_enabled": True,
                "reason": "shadow_mode_computes_capability_but_executes_legacy",
                "policy_action": policy_decision.action.value,
                "policy_allowed": policy_allows,
                "capability_exists": capability_exists,
                "rollout_enabled": rollout_enabled,
            }

        if not policy_allows:
            runtime_action = str((policy_decision.metadata or {}).get("runtime_action") or "").strip().lower()
            deny_reason = "policy_denied_or_requires_approval"
            if runtime_action in {"force_legacy_fallback", "disable_capability", "restrict_scope"}:
                deny_reason = "policy_forced_legacy_fallback"
            return {
                "routing_mode": routing_mode,
                "selected_capability_id": capability_id,
                "execute_capability": False,
                "use_legacy": True,
                "shadow_enabled": True,
                "reason": deny_reason,
                "policy_action": policy_decision.action.value,
                "policy_allowed": False,
                "policy_runtime_action": runtime_action or None,
                "capability_exists": capability_exists,
                "rollout_enabled": rollout_enabled,
            }

        if not capability_exists:
            return {
                "routing_mode": routing_mode,
                "selected_capability_id": capability_id,
                "execute_capability": False,
                "use_legacy": True,
                "shadow_enabled": True,
                "reason": "capability_not_found",
                "policy_action": policy_decision.action.value,
                "policy_allowed": True,
                "capability_exists": False,
                "rollout_enabled": rollout_enabled,
            }

        if not rollout_enabled:
            return {
                "routing_mode": routing_mode,
                "selected_capability_id": capability_id,
                "execute_capability": False,
                "use_legacy": True,
                "shadow_enabled": True,
                "reason": "capability_rollout_disabled",
                "policy_action": policy_decision.action.value,
                "policy_allowed": True,
                "capability_exists": capability_exists,
                "rollout_enabled": False,
            }

        if capability_domain in {"attendance", "transport"}:
            return {
                "routing_mode": routing_mode,
                "selected_capability_id": capability_id,
                "execute_capability": True,
                "use_legacy": False,
                "shadow_enabled": True,
                "reason": f"capability_mode_{capability_domain}_execution_enabled",
                "policy_action": policy_decision.action.value,
                "policy_allowed": True,
                "capability_exists": capability_exists,
                "rollout_enabled": rollout_enabled,
            }

        return {
            "routing_mode": routing_mode,
            "selected_capability_id": capability_id,
            "execute_capability": False,
            "use_legacy": True,
            "shadow_enabled": True,
            "reason": "capability_mode_domain_not_enabled_yet",
            "policy_action": policy_decision.action.value,
            "policy_allowed": True,
            "capability_exists": capability_exists,
            "rollout_enabled": rollout_enabled,
        }

    def execute(
        self,
        *,
        run_context: RunContext,
        route: dict[str, Any],
        planned_capability: dict[str, Any],
        message: str,
        session_id: str | None,
        reset_memory: bool,
        memory_context: dict[str, Any] | None = None,
        observability=None,
    ) -> dict[str, Any]:
        if not bool(route.get("execute_capability")):
            return {
                "ok": False,
                "error": "route_does_not_execute_capability",
                "meta": {"reason": route.get("reason")},
            }

        capability_id = str(planned_capability.get("capability_id") or route.get("selected_capability_id") or "")
        if capability_id.startswith("attendance."):
            result = self._get_attendance_handler().handle(
                capability_id=capability_id,
                message=message,
                session_id=session_id,
                reset_memory=reset_memory,
                run_context=run_context,
                planned_capability=planned_capability,
                memory_context=memory_context,
                observability=observability,
            )
            return {
                "ok": bool(result.ok),
                "response": result.response,
                "error": result.error,
                "meta": dict(result.metadata or {}),
            }
        if capability_id.startswith("transport."):
            result = self._get_transport_handler().handle(
                capability_id=capability_id,
                message=message,
                session_id=session_id,
                reset_memory=reset_memory,
                run_context=run_context,
                planned_capability=planned_capability,
                memory_context=memory_context,
                observability=observability,
            )
            return {
                "ok": bool(result.ok),
                "response": result.response,
                "error": result.error,
                "meta": dict(result.metadata or {}),
            }

        return {
            "ok": False,
            "error": f"unsupported_capability_domain:{capability_id}",
            "meta": {"capability_id": capability_id},
        }

    def _get_attendance_handler(self) -> AttendanceHandler:
        if self._attendance_handler is None:
            self._attendance_handler = AttendanceHandler()
        return self._attendance_handler

    def _get_transport_handler(self) -> TransportHandler:
        if self._transport_handler is None:
            self._transport_handler = TransportHandler()
        return self._transport_handler
