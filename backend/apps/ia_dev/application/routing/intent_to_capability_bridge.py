from __future__ import annotations

from typing import Any


class IntentToCapabilityBridge:
    _ITEMIZED_TOKENS = (
        "dia a dia",
        "por ausentismo",
        "fecha por fecha",
        "registro por registro",
        "detalle por dia",
        "itemizado",
    )
    _GROUPED_TOKENS = (
        "agrupado",
        "resumen por empleado",
        "por empleado",
    )
    _SUMMARY_TOKENS = (
        "resumen",
        "kpi",
        "totales",
        "total de",
    )
    _TABLE_TOKENS = (
        "tabla",
        "lista",
        "detalle",
        "mostrar",
    )
    _PERSONAL_TOKENS = (
        "empleado",
        "personal",
        "supervisor",
        "area",
        "cargo",
        "nombre",
        "apellido",
    )

    @staticmethod
    def _normalize(text: str) -> str:
        return str(text or "").strip().lower()

    def resolve(
        self,
        *,
        message: str,
        classification: dict[str, Any],
    ) -> dict[str, Any]:
        msg = self._normalize(message)
        intent = str(classification.get("intent") or "general_question")
        domain = str(classification.get("domain") or "general")
        output_mode = str(classification.get("output_mode") or "summary")
        needs_database = bool(classification.get("needs_database"))
        used_tools = list(classification.get("used_tools") or [])
        needs_personal_join = bool(classification.get("needs_personal_join"))

        capability_id = "legacy.passthrough.v1"
        reason = "fallback_to_legacy"

        if intent == "attendance_period_probe":
            capability_id = "attendance.period.resolve.v1"
            reason = "legacy_intent_match_attendance_period_probe"
        elif intent == "knowledge_change_request":
            capability_id = "knowledge.proposal.create.v1"
            reason = "legacy_intent_match_knowledge_change_request"
        elif domain == "attendance":
            wants_itemized = any(token in msg for token in self._ITEMIZED_TOKENS)
            wants_grouped = any(token in msg for token in self._GROUPED_TOKENS)
            wants_summary = any(token in msg for token in self._SUMMARY_TOKENS)
            wants_table = any(token in msg for token in self._TABLE_TOKENS)
            wants_personal_join = needs_personal_join or any(
                token in msg for token in self._PERSONAL_TOKENS
            )
            is_recurrence = (
                "get_attendance_recurrent_unjustified_with_supervisor" in used_tools
                or intent == "attendance_recurrence"
                or "reincid" in msg
            )

            if is_recurrence:
                wants_itemized = (
                    wants_itemized
                    or "get_attendance_unjustified_with_personal" in used_tools
                )
                if wants_grouped and not wants_itemized:
                    capability_id = "attendance.recurrence.grouped.v1"
                    reason = "attendance_recurrence_grouped_detected"
                else:
                    capability_id = (
                        "attendance.recurrence.itemized.v1"
                        if wants_itemized
                        else "attendance.recurrence.grouped.v1"
                    )
                    reason = "attendance_recurrence_detected"
            elif "get_attendance_summary" in used_tools or (
                output_mode == "summary" and not wants_table
            ) or (wants_summary and not wants_table):
                capability_id = "attendance.unjustified.summary.v1"
                reason = "attendance_summary_detected"
            elif (
                "get_attendance_unjustified_with_personal" in used_tools
                or "get_attendance_detail_with_personal" in used_tools
                or wants_personal_join
            ):
                capability_id = "attendance.unjustified.table_with_personal.v1"
                reason = "attendance_table_with_personal_detected"
            else:
                capability_id = "attendance.unjustified.table.v1"
                reason = "attendance_table_detected"
        elif not needs_database:
            capability_id = "general.answer.v1"
            reason = "legacy_general_no_database"
        elif domain == "general":
            capability_id = "general.answer.v1"
            reason = "legacy_general_domain"

        return {
            "capability_id": capability_id,
            "reason": reason,
            "source_intent": intent,
            "source_domain": domain,
            "output_mode": output_mode,
            "needs_database": needs_database,
        }

    def compare(
        self,
        *,
        classification: dict[str, Any],
        planned_capability: dict[str, Any],
    ) -> dict[str, Any]:
        intent = str(classification.get("intent") or "")
        domain = str(classification.get("domain") or "general")
        capability_id = str(planned_capability.get("capability_id") or "legacy.passthrough.v1")
        capability_domain = capability_id.split(".", 1)[0] if "." in capability_id else "legacy"

        if capability_domain == "legacy":
            diverged = False
            reason = "legacy_passthrough"
        elif intent == "knowledge_change_request":
            diverged = capability_domain != "knowledge"
            reason = "knowledge_capability_expected"
        elif domain == "attendance":
            diverged = capability_domain != "attendance"
            reason = "attendance_capability_expected"
        elif domain == "general":
            diverged = capability_domain not in ("general", "knowledge")
            reason = "general_capability_expected"
        else:
            diverged = False
            reason = "domain_not_mapped_in_pr1"

        return {
            "legacy_intent": intent,
            "legacy_domain": domain,
            "planned_capability_id": capability_id,
            "planned_capability_domain": capability_domain,
            "diverged": bool(diverged),
            "reason": reason,
        }
