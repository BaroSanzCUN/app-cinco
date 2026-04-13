from __future__ import annotations

import unicodedata
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
        "cantidad",
        "cuantos",
        "cuantas",
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
    _TRANSPORT_TOKENS = (
        "transporte",
        "ruta",
        "movilidad",
        "vehiculo",
        "vehiculos",
        "salieron",
        "salidas",
    )
    _EMPLOYEES_TOKENS = (
        "empleado",
        "empleados",
        "cedula",
        "cedulas",
        "rrhh",
        "recurso humano",
        "recursos humanos",
    )
    _ACTIVE_STATUS_TOKENS = (
        "activo",
        "activos",
        "empleados activos",
    )
    _TREND_TOKENS = (
        "tendencia",
        "evolucion",
        "comportamiento",
        "historico",
        "historica",
    )
    _MONTHLY_TOKENS = (
        "mensual",
        "por mes",
        "mes a mes",
        "mes anterior",
        "ultimo mes",
        "ultimos meses",
    )
    _DAILY_TOKENS = (
        "diaria",
        "diario",
        "por dia",
        "dia a dia",
    )
    _CHART_TOKENS = (
        "grafica",
        "grafico",
        "chart",
        "linea",
        "barras",
        "barra",
    )
    _ANALYTICS_TOKENS = (
        "comparativo",
        "distribucion",
        "top",
        "cantidad",
        "total",
        "resumen",
    )
    _BY_SUPERVISOR_TOKENS = (
        "por supervisor",
        "supervisor",
    )
    _BY_AREA_TOKENS = (
        "por area",
        "area",
    )
    _BY_CARGO_TOKENS = (
        "por cargo",
        "cargo",
    )
    _BY_CARPETA_TOKENS = (
        "por carpeta",
        "carpeta",
    )
    _BY_JUSTIFICACION_TOKENS = (
        "por justificacion",
        "justificacion",
        "por motivo",
        "motivo",
        "por causa",
        "causa",
    )
    _BY_TIPO_TOKENS = (
        "por tipo",
        "tipo",
        "por estado",
        "estado",
    )
    _COMPARATIVE_TOKENS = (
        "comparativo",
        "comparar",
        "vs",
        "versus",
        "contra",
    )
    _DISTRIBUTION_TOKENS = (
        "distribucion",
        "distribucion porcentual",
        "participacion",
        "participacion porcentual",
    )
    _TOP_TOKENS = (
        "top",
        "top 5",
        "top 10",
    )

    @staticmethod
    def _normalize(text: str) -> str:
        lowered = str(text or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

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
        mentions_attendance = any(
            token in msg for token in ("ausent", "asistenc", "injustific", "justific", "incapacidad", "vacaciones")
        )

        capability_id = "legacy.passthrough.v1"
        reason = "fallback_to_legacy"

        if intent == "attendance_period_probe":
            capability_id = "attendance.period.resolve.v1"
            reason = "legacy_intent_match_attendance_period_probe"
        elif intent == "knowledge_change_request":
            capability_id = "knowledge.proposal.create.v1"
            reason = "legacy_intent_match_knowledge_change_request"
        elif domain == "attendance" or mentions_attendance:
            wants_itemized = any(token in msg for token in self._ITEMIZED_TOKENS)
            wants_grouped = any(token in msg for token in self._GROUPED_TOKENS)
            wants_summary = any(token in msg for token in self._SUMMARY_TOKENS)
            wants_table = any(token in msg for token in self._TABLE_TOKENS)
            wants_chart = any(token in msg for token in self._CHART_TOKENS)
            wants_trend = any(token in msg for token in self._TREND_TOKENS)
            wants_monthly = any(token in msg for token in self._MONTHLY_TOKENS)
            wants_daily = any(token in msg for token in self._DAILY_TOKENS)
            wants_analytics = wants_chart or wants_trend or any(
                token in msg for token in self._ANALYTICS_TOKENS
            )
            wants_by_supervisor = any(token in msg for token in self._BY_SUPERVISOR_TOKENS)
            wants_by_area = any(token in msg for token in self._BY_AREA_TOKENS)
            wants_by_cargo = any(token in msg for token in self._BY_CARGO_TOKENS)
            wants_by_carpeta = any(token in msg for token in self._BY_CARPETA_TOKENS)
            wants_by_justificacion = any(token in msg for token in self._BY_JUSTIFICACION_TOKENS)
            wants_by_tipo = any(token in msg for token in self._BY_TIPO_TOKENS)
            wants_group_dimension = any(
                (
                    wants_by_supervisor,
                    wants_by_area,
                    wants_by_cargo,
                    wants_by_carpeta,
                    wants_by_justificacion,
                    wants_by_tipo,
                )
            )
            contextual_reference = bool(classification.get("contextual_reference"))
            last_group_dimension_key = str(classification.get("last_group_dimension_key") or "").strip().lower()
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
            elif (
                wants_chart
                and contextual_reference
                and last_group_dimension_key
                and not (wants_trend or wants_monthly or wants_daily)
            ):
                if last_group_dimension_key == "supervisor":
                    capability_id = "attendance.summary.by_supervisor.v1"
                    reason = "attendance_followup_chart_from_context_supervisor"
                elif last_group_dimension_key == "area":
                    capability_id = "attendance.summary.by_area.v1"
                    reason = "attendance_followup_chart_from_context_area"
                elif last_group_dimension_key == "cargo":
                    capability_id = "attendance.summary.by_cargo.v1"
                    reason = "attendance_followup_chart_from_context_cargo"
                else:
                    capability_id = "attendance.summary.by_attribute.v1"
                    reason = "attendance_followup_chart_from_context_attribute"
            elif wants_trend or (wants_chart and ("tendencia" in msg or "evolucion" in msg)):
                capability_id = (
                    "attendance.trend.monthly.v1"
                    if wants_monthly and not wants_daily
                    else "attendance.trend.daily.v1"
                )
                reason = "attendance_trend_detected"
            elif wants_by_supervisor and wants_analytics:
                capability_id = "attendance.summary.by_supervisor.v1"
                reason = "attendance_summary_by_supervisor_detected"
            elif wants_by_area and wants_analytics:
                capability_id = "attendance.summary.by_area.v1"
                reason = "attendance_summary_by_area_detected"
            elif wants_by_cargo and wants_analytics:
                capability_id = "attendance.summary.by_cargo.v1"
                reason = "attendance_summary_by_cargo_detected"
            elif wants_group_dimension and (wants_analytics or wants_summary):
                capability_id = "attendance.summary.by_attribute.v1"
                reason = "attendance_summary_by_attribute_detected"
            elif wants_chart and not wants_table:
                capability_id = (
                    "attendance.trend.monthly.v1"
                    if wants_monthly and not wants_daily
                    else "attendance.trend.daily.v1"
                )
                reason = "attendance_chart_detected"
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
        elif domain in {"empleados", "rrhh"} or any(token in msg for token in self._EMPLOYEES_TOKENS):
            wants_count = any(token in msg for token in self._SUMMARY_TOKENS)
            wants_active = any(token in msg for token in self._ACTIVE_STATUS_TOKENS)
            if wants_count and wants_active:
                capability_id = "empleados.count.active.v1"
                reason = "empleados_count_active_detected"
            else:
                capability_id = "general.answer.v1"
                reason = "empleados_query_without_supported_capability"
        elif not needs_database:
            capability_id = "general.answer.v1"
            reason = "legacy_general_no_database"
        elif domain == "transport" or intent == "transport_query" or any(
            token in msg for token in self._TRANSPORT_TOKENS
        ):
            capability_id = "transport.departures.summary.v1"
            reason = "transport_departures_detected"
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
        elif domain == "transport":
            diverged = capability_domain != "transport"
            reason = "transport_capability_expected"
        elif domain in {"empleados", "rrhh"}:
            diverged = capability_domain != "empleados"
            reason = "empleados_capability_expected"
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

    def resolve_candidates(
        self,
        *,
        message: str,
        classification: dict[str, Any],
        max_candidates: int = 4,
    ) -> list[dict[str, Any]]:
        signals = self._semantic_signals(message)
        primary = self.resolve(message=message, classification=classification)
        primary["semantic_signals"] = dict(signals)
        candidates: list[dict[str, Any]] = [dict(primary)]

        domain = str(classification.get("domain") or "").strip().lower()
        needs_database = bool(classification.get("needs_database"))
        contextual_reference = bool(classification.get("contextual_reference"))
        last_group_dimension_key = str(
            classification.get("last_group_dimension_key") or ""
        ).strip().lower()

        def add(capability_id: str, reason: str) -> None:
            if not capability_id:
                return
            candidates.append(
                {
                    "capability_id": capability_id,
                    "reason": reason,
                    "source_intent": str(classification.get("intent") or ""),
                    "source_domain": str(classification.get("domain") or "general"),
                    "output_mode": str(classification.get("output_mode") or "summary"),
                    "needs_database": needs_database,
                    "semantic_signals": signals,
                }
            )

        if domain == "attendance":
            if (
                signals["wants_chart"]
                and contextual_reference
                and last_group_dimension_key
                and not (signals["wants_trend"] or signals["wants_monthly"] or signals["wants_daily"])
            ):
                if last_group_dimension_key == "supervisor":
                    add(
                        "attendance.summary.by_supervisor.v1",
                        "semantic_followup_chart_from_context_supervisor",
                    )
                elif last_group_dimension_key == "area":
                    add(
                        "attendance.summary.by_area.v1",
                        "semantic_followup_chart_from_context_area",
                    )
                elif last_group_dimension_key == "cargo":
                    add(
                        "attendance.summary.by_cargo.v1",
                        "semantic_followup_chart_from_context_cargo",
                    )
                else:
                    add(
                        "attendance.summary.by_attribute.v1",
                        "semantic_followup_chart_from_context_attribute",
                    )
            if signals["wants_trend"] or signals["wants_comparative"]:
                add("attendance.trend.monthly.v1", "semantic_alt_monthly_trend")
                add("attendance.trend.daily.v1", "semantic_alt_daily_trend")
            if signals["wants_chart"] and not signals["wants_trend"]:
                add("attendance.trend.daily.v1", "semantic_chart_daily_trend")
                add("attendance.trend.monthly.v1", "semantic_chart_monthly_trend")
            if signals["wants_by_supervisor"]:
                add("attendance.summary.by_supervisor.v1", "semantic_alt_group_supervisor")
            if signals["wants_by_area"]:
                add("attendance.summary.by_area.v1", "semantic_alt_group_area")
            if signals["wants_by_cargo"]:
                add("attendance.summary.by_cargo.v1", "semantic_alt_group_cargo")
            if signals["wants_group_dimension"] and not (
                signals["wants_by_supervisor"] or signals["wants_by_area"] or signals["wants_by_cargo"]
            ):
                add("attendance.summary.by_attribute.v1", "semantic_alt_group_attribute")
            if signals["wants_distribution"]:
                add("attendance.summary.by_area.v1", "semantic_distribution_area")
                add("attendance.summary.by_cargo.v1", "semantic_distribution_cargo")
            if signals["wants_top"]:
                add("attendance.summary.by_supervisor.v1", "semantic_top_supervisor")

        if domain in {"empleados", "rrhh"} or signals["mentions_empleados"]:
            if signals["wants_count"] and signals["wants_active"]:
                add("empleados.count.active.v1", "semantic_empleados_count_active")

        if domain in {"general", "rrhh"} and needs_database and (
            signals["mentions_attendance"] or signals["wants_trend"] or signals["wants_chart"]
        ):
            # Reduce fallback erratico a general/rrhh cuando semantica sugiere attendance analytics.
            add("attendance.summary.by_supervisor.v1", "semantic_recovery_from_general_or_rrhh")
            if signals["wants_group_dimension"]:
                add("attendance.summary.by_attribute.v1", "semantic_recovery_attendance_group_attribute")
            add("attendance.trend.daily.v1", "semantic_recovery_attendance_trend")

        if domain == "general" and signals["mentions_transport"] and needs_database:
            add("transport.departures.summary.v1", "semantic_recovery_transport")

        deduped: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for candidate in candidates:
            capability_id = str(candidate.get("capability_id") or "").strip()
            if not capability_id or capability_id in seen_ids:
                continue
            seen_ids.add(capability_id)
            deduped.append(candidate)
            if len(deduped) >= max(1, int(max_candidates)):
                break
        return deduped

    def _semantic_signals(self, message: str) -> dict[str, bool]:
        msg = self._normalize(message)
        return {
            "wants_chart": any(token in msg for token in self._CHART_TOKENS),
            "wants_trend": any(token in msg for token in self._TREND_TOKENS),
            "wants_count": any(token in msg for token in self._SUMMARY_TOKENS),
            "wants_monthly": any(token in msg for token in self._MONTHLY_TOKENS),
            "wants_daily": any(token in msg for token in self._DAILY_TOKENS),
            "wants_comparative": any(token in msg for token in self._COMPARATIVE_TOKENS),
            "wants_distribution": any(token in msg for token in self._DISTRIBUTION_TOKENS),
            "wants_top": any(token in msg for token in self._TOP_TOKENS),
            "wants_active": any(token in msg for token in self._ACTIVE_STATUS_TOKENS),
            "wants_by_supervisor": any(token in msg for token in self._BY_SUPERVISOR_TOKENS),
            "wants_by_area": any(token in msg for token in self._BY_AREA_TOKENS),
            "wants_by_cargo": any(token in msg for token in self._BY_CARGO_TOKENS),
            "wants_group_dimension": any(
                token in msg
                for token in (
                    *self._BY_SUPERVISOR_TOKENS,
                    *self._BY_AREA_TOKENS,
                    *self._BY_CARGO_TOKENS,
                    *self._BY_CARPETA_TOKENS,
                    *self._BY_JUSTIFICACION_TOKENS,
                    *self._BY_TIPO_TOKENS,
                )
            ),
            "mentions_attendance": any(token in msg for token in ("ausent", "asistencia", "injustific", "reincid")),
            "mentions_empleados": any(token in msg for token in self._EMPLOYEES_TOKENS),
            "mentions_transport": any(token in msg for token in self._TRANSPORT_TOKENS),
        }
