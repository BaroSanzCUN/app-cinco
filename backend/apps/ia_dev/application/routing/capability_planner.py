from __future__ import annotations

import os
from typing import Any

from apps.ia_dev.application.policies.policy_runtime import PolicyRuntime
from apps.ia_dev.application.routing.capability_catalog import CapabilityCatalog
from apps.ia_dev.application.routing.intent_to_capability_bridge import (
    IntentToCapabilityBridge,
)


class CapabilityPlanner:
    def __init__(
        self,
        *,
        catalog: CapabilityCatalog | None = None,
        bridge: IntentToCapabilityBridge | None = None,
        policy_runtime: PolicyRuntime | None = None,
    ):
        self.catalog = catalog or CapabilityCatalog()
        self.bridge = bridge or IntentToCapabilityBridge()
        self.policy_runtime = policy_runtime or PolicyRuntime()

    def plan_from_legacy(
        self,
        *,
        message: str,
        classification: dict[str, Any],
        planning_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        candidates = self.plan_candidates_from_legacy(
            message=message,
            classification=classification,
            planning_context=planning_context,
            max_candidates=1,
        )
        if candidates:
            return dict(candidates[0])
        return self._build_plan(
            mapped={
                "capability_id": "legacy.passthrough.v1",
                "reason": "planner_no_candidates",
                "source_intent": str(classification.get("intent") or ""),
                "source_domain": str(classification.get("domain") or "general"),
                "output_mode": str(classification.get("output_mode") or "summary"),
                "needs_database": bool(classification.get("needs_database")),
            },
            classification=classification,
            planning_context=planning_context,
            candidate_rank=1,
            candidate_score=0,
        )

    def plan_candidates_from_legacy(
        self,
        *,
        message: str,
        classification: dict[str, Any],
        planning_context: dict[str, Any] | None = None,
        max_candidates: int = 4,
    ) -> list[dict[str, Any]]:
        planning_context = dict(planning_context or {})
        max_candidates = max(1, min(int(max_candidates), 8))

        if hasattr(self.bridge, "resolve_candidates"):
            mapped_candidates = self.bridge.resolve_candidates(
                message=message,
                classification=classification,
                max_candidates=max_candidates,
            )
        else:
            mapped_candidates = [self.bridge.resolve(message=message, classification=classification)]

        scored: list[tuple[int, int, dict[str, Any]]] = []
        for idx, mapped in enumerate(mapped_candidates):
            score = self._score_mapped_candidate(
                message=message,
                mapped=mapped,
                planning_context=planning_context,
                rank_hint=idx + 1,
            )
            plan = self._build_plan(
                mapped=mapped,
                classification=classification,
                planning_context=planning_context,
                candidate_rank=idx + 1,
                candidate_score=score,
            )
            scored.append((score, -(idx + 1), plan))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        plans = [item[2] for item in scored[:max_candidates]]
        for idx, plan in enumerate(plans, start=1):
            plan["candidate_rank"] = idx
        return plans

    def _build_plan(
        self,
        *,
        mapped: dict[str, Any],
        classification: dict[str, Any],
        planning_context: dict[str, Any] | None,
        candidate_rank: int,
        candidate_score: int,
    ) -> dict[str, Any]:
        capability_id = str(mapped.get("capability_id") or "legacy.passthrough.v1")
        definition = self.catalog.get(capability_id)
        rollout_enabled = self._rollout_enabled(definition)
        dictionary_hints = self._dictionary_hints(classification.get("dictionary_context"))
        source = {
            "intent": str(mapped.get("source_intent") or ""),
            "domain": str(mapped.get("source_domain") or ""),
            "output_mode": str(mapped.get("output_mode") or "summary"),
            "needs_database": bool(mapped.get("needs_database")),
        }
        planning_context = dict(planning_context or {})
        policy_planner_hint = self._policy_planner_hint(
            capability_id=capability_id,
            policy_tags=list(definition.policy_tags) if definition else [],
            source=source,
            planning_context=planning_context,
        )

        return {
            "capability_id": capability_id,
            "capability_exists": bool(definition),
            "rollout_enabled": rollout_enabled,
            "handler_key": definition.handler_key if definition else "legacy.passthrough",
            "policy_tags": list(definition.policy_tags) if definition else [],
            "legacy_intents": list(definition.legacy_intents) if definition else [],
            "reason": str(mapped.get("reason") or "unspecified"),
            "source": source,
            "dictionary_hints": dictionary_hints,
            "policy_planner_hint": policy_planner_hint,
            "semantic_signals": dict(mapped.get("semantic_signals") or {}),
            "candidate_rank": int(candidate_rank),
            "candidate_score": int(candidate_score),
            "workflow_hints": dict(planning_context.get("workflow_hints") or {}),
        }

    @staticmethod
    def _rollout_enabled(definition) -> bool:
        if not definition or not definition.rollout_flag:
            return True
        raw_flag = str(definition.rollout_flag or "").strip()
        if not raw_flag:
            return True
        required_flags = [
            token.strip()
            for token in raw_flag.replace(",", "|").split("|")
            if token.strip()
        ]
        if not required_flags:
            return True
        for name in required_flags:
            value = CapabilityPlanner._resolve_rollout_flag_value(name)
            if value not in {"1", "true", "yes", "on"}:
                return False
        return True

    @staticmethod
    def _resolve_rollout_flag_value(name: str) -> str:
        aliases = {
            "IA_DEV_CAP_ATTENDANCE_SUMMARY_ENABLED": ("IA_DEV_CAP_ATTENDANCE_SUMMARY_V1",),
            "IA_DEV_CAP_ATTENDANCE_TABLE_ENABLED": (
                "IA_DEV_CAP_ATTENDANCE_TABLE_V1",
                "IA_DEV_CAP_ATTENDANCE_TABLE_WITH_PERSONAL_V1",
            ),
            "IA_DEV_CAP_ATTENDANCE_RECURRENCE_ENABLED": (
                "IA_DEV_CAP_ATTENDANCE_RECURRENCE_GROUPED_V1",
                "IA_DEV_CAP_ATTENDANCE_RECURRENCE_ITEMIZED_V1",
            ),
            "IA_DEV_CAP_ATTENDANCE_ANALYTICS_ENABLED": (
                "IA_DEV_CAP_ATTENDANCE_ANALYTICS_V1",
                "IA_DEV_CAP_ATTENDANCE_SUMMARY_BY_SUPERVISOR_V1",
                "IA_DEV_CAP_ATTENDANCE_SUMMARY_BY_AREA_V1",
                "IA_DEV_CAP_ATTENDANCE_SUMMARY_BY_CARGO_V1",
                "IA_DEV_CAP_ATTENDANCE_TREND_DAILY_V1",
                "IA_DEV_CAP_ATTENDANCE_TREND_MONTHLY_V1",
            ),
            "IA_DEV_CAP_TRANSPORT_SUMMARY_ENABLED": ("IA_DEV_CAP_TRANSPORT_SUMMARY_V1",),
        }
        candidates = (name, *aliases.get(name, ()))
        for key in candidates:
            if key in os.environ:
                return str(os.getenv(key, "")).strip().lower()
        default = "0" if (name.startswith("IA_DEV_CAP_ATTENDANCE") or name.startswith("IA_DEV_CAP_TRANSPORT")) else "1"
        return str(os.getenv(name, default)).strip().lower()

    @staticmethod
    def _dictionary_hints(raw_context: Any) -> dict[str, Any]:
        context = raw_context if isinstance(raw_context, dict) else {}
        tables = context.get("tables") if isinstance(context.get("tables"), list) else []
        fields = context.get("fields") if isinstance(context.get("fields"), list) else []
        relations = (
            context.get("relations")
            if isinstance(context.get("relations"), list)
            else []
        )
        domain = context.get("domain") if isinstance(context.get("domain"), dict) else {}
        return {
            "domain_code": str(domain.get("code") or ""),
            "table_count": len(tables),
            "field_count": len(fields),
            "relation_count": len(relations),
            "table_names": [
                str(item.get("table_name") or "")
                for item in tables[:8]
                if isinstance(item, dict) and item.get("table_name")
            ],
        }

    def _policy_planner_hint(
        self,
        *,
        capability_id: str,
        policy_tags: list[str],
        source: dict[str, Any],
        planning_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not capability_id:
            return {}
        if os.getenv("IA_DEV_POLICY_RUNTIME_ENABLED", "1").strip().lower() not in {"1", "true", "yes", "on"}:
            return {}
        requires_personal_join = capability_id in {
            "attendance.unjustified.table_with_personal.v1",
            "attendance.recurrence.grouped.v1",
            "attendance.recurrence.itemized.v1",
            "attendance.summary.by_supervisor.v1",
            "attendance.summary.by_area.v1",
            "attendance.summary.by_cargo.v1",
        }
        memory_hints = dict((planning_context or {}).get("memory_hints") or {})
        uses_memory_hints = bool(memory_hints)
        try:
            decision = self.policy_runtime.evaluate(
                policy_name="capability_runtime_policy.yaml",
                context={
                    "routing_mode": os.getenv("IA_DEV_ROUTING_MODE", "intent"),
                    "capability_id": capability_id,
                    "needs_database": bool(source.get("needs_database", True)),
                    "requires_personal_join": requires_personal_join,
                    "policy_tags": list(policy_tags or []),
                    "uses_memory_hints": uses_memory_hints,
                },
                fallback_action="allow",
                fallback_policy_id="planner.policy_runtime.fallback",
                fallback_reason="planner_policy_hint_fallback",
            )
        except Exception:
            return {}
        return {
            "action": str(decision.action or ""),
            "policy_id": str(decision.policy_id or ""),
            "reason": str(decision.reason or ""),
            "metadata": dict(decision.metadata or {}),
        }

    @staticmethod
    def _score_mapped_candidate(
        *,
        message: str,
        mapped: dict[str, Any],
        planning_context: dict[str, Any],
        rank_hint: int,
    ) -> int:
        capability_id = str(mapped.get("capability_id") or "")
        reason = str(mapped.get("reason") or "")
        semantic = dict(mapped.get("semantic_signals") or {})
        memory_hints = dict(planning_context.get("memory_hints") or {})
        workflow_hints = dict(planning_context.get("workflow_hints") or {})

        score = max(0, 100 - (max(1, int(rank_hint)) - 1) * 10)
        if "fallback" in reason:
            score -= 5

        if semantic.get("wants_trend") and capability_id.startswith("attendance.trend."):
            score += 12
        if semantic.get("wants_chart") and (
            capability_id.startswith("attendance.summary.by_") or capability_id.startswith("attendance.trend.")
        ):
            score += 8
        if semantic.get("wants_comparative"):
            if capability_id == "attendance.trend.monthly.v1":
                score += 20
            elif capability_id.startswith("attendance.summary.by_"):
                score -= 6
        if semantic.get("wants_monthly") and capability_id == "attendance.trend.monthly.v1":
            score += 10
        if semantic.get("wants_daily") and capability_id == "attendance.trend.daily.v1":
            score += 8
        if semantic.get("wants_distribution") and capability_id.startswith("attendance.summary.by_"):
            score += 8
        if semantic.get("wants_top") and capability_id.startswith("attendance.summary.by_"):
            score += 4
        if semantic.get("mentions_transport") and capability_id.startswith("transport."):
            score += 8

        recurrence_view = str(memory_hints.get("recurrence_view") or "").strip().lower()
        if recurrence_view == "itemized" and capability_id == "attendance.recurrence.itemized.v1":
            score += 6
        if recurrence_view == "grouped" and capability_id == "attendance.recurrence.grouped.v1":
            score += 6
        chart_type = str(memory_hints.get("analytics_chart_type") or "").strip().lower()
        if chart_type and capability_id.startswith("attendance.trend."):
            score += 3

        pending_count = int(workflow_hints.get("pending_count") or 0)
        if pending_count > 0 and capability_id.startswith("knowledge."):
            score += 2

        normalized_message = str(message or "").strip().lower()
        if "por supervisor" in normalized_message and capability_id == "attendance.summary.by_supervisor.v1":
            score += 5
        if "por area" in normalized_message and capability_id == "attendance.summary.by_area.v1":
            score += 5
        if "por cargo" in normalized_message and capability_id == "attendance.summary.by_cargo.v1":
            score += 5

        return int(score)
