from __future__ import annotations

import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from apps.ia_dev.TOOLS.business.attendance_business_tool import (
    AttendanceBusinessTool,
    AttendancePeriod,
)
from apps.ia_dev.application.context.run_context import RunContext
from apps.ia_dev.services.memory_service import SessionMemoryStore
from apps.ia_dev.services.period_service import resolve_period_from_text


logger = logging.getLogger(__name__)

_YES_FOLLOW_UP_RE = re.compile(
    r"^((si)([,! ]+por favor)?|ok|dale|perfecto|claro|adelante|continua|por favor)[.! ]*$",
    re.IGNORECASE,
)


@dataclass(slots=True)
class AttendanceHandleResult:
    ok: bool
    response: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


class AttendanceHandler:
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
    _PERSONAL_TOKENS = (
        "personal",
        "empleado",
        "supervisor",
        "area",
        "cargo",
        "nombre",
        "apellido",
    )

    def __init__(self, *, tool: AttendanceBusinessTool | None = None):
        self.tool = tool or AttendanceBusinessTool()

    def handle(
        self,
        *,
        capability_id: str,
        message: str,
        session_id: str | None,
        reset_memory: bool,
        run_context: RunContext,
        planned_capability: dict[str, Any],
        memory_context: dict[str, Any] | None = None,
        observability=None,
    ) -> AttendanceHandleResult:
        sid, _ = SessionMemoryStore.get_or_create(session_id)
        if reset_memory:
            SessionMemoryStore.reset(sid)

        started_at = time.perf_counter()
        tool_latencies_ms: dict[str, int] = {}
        trace: list[dict[str, Any]] = []
        used_tools: list[str] = []
        payload = {
            "kpis": {},
            "series": [],
            "labels": [],
            "insights": [],
            "table": {"columns": [], "rows": [], "rowcount": 0},
        }
        actions: list[dict[str, Any]] = []

        def _push_trace(phase: str, status: str, detail: Any, active_nodes: list[str] | None = None) -> None:
            trace.append(
                {
                    "phase": phase,
                    "status": status,
                    "at": datetime.now(timezone.utc).isoformat(),
                    "detail": detail,
                    "active_nodes": active_nodes or ["q", "gpt", "route", "aus", "result"],
                }
            )

        def _measure_tool(name: str, fn, *args, **kwargs):
            t0 = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                duration_ms = int((time.perf_counter() - t0) * 1000)
                tool_latencies_ms[name] = duration_ms
                if observability is not None and hasattr(observability, "record_event"):
                    observability.record_event(
                        event_type="tool_latency",
                        source=name,
                        duration_ms=duration_ms,
                        meta={"session_id": sid, "run_id": run_context.run_id},
                    )

        try:
            session_context = SessionMemoryStore.get_context(sid)
            period = self._resolve_period_for_attendance(
                message=message,
                session_context=session_context,
            )
            memory_hints = self._extract_memory_hints(memory_context)
            memory_hints_used: list[dict[str, Any]] = []
            personal_status = self._resolve_personal_status(
                message=message,
                session_context=session_context,
                hints=memory_hints,
                used=memory_hints_used,
            )
            _push_trace(
                "period_resolver",
                "ok",
                {
                    "label": period.label,
                    "source": period.source,
                    "start": period.start.isoformat(),
                    "end": period.end.isoformat(),
                    "personal_status": personal_status,
                },
                ["q", "route", "rules", "aus"],
            )

            response_output_mode = "table"
            intent = "attendance_query"
            focus = "unjustified"
            needs_personal_join = False
            reply = ""

            if capability_id == "attendance.unjustified.summary.v1":
                summary = _measure_tool(
                    "attendance_get_summary",
                    self.tool.get_unjustified_summary,
                    period=period,
                )
                used_tools.append("get_attendance_summary")
                response_output_mode = "summary"
                payload["kpis"] = {
                    "total_ausentismos": int(summary.get("total_ausentismos") or 0),
                    "justificados": int(summary.get("justificados") or 0),
                    "injustificados": int(summary.get("injustificados") or 0),
                }
                payload["insights"] = [
                    f"Periodo: {summary.get('periodo_inicio')} a {summary.get('periodo_fin')}",
                    "Puedes pedir tabla por empleado, supervisor, area o cargo.",
                ]
                reply = (
                    f"Resumen de ausentismo del periodo {summary.get('periodo_inicio')} al {summary.get('periodo_fin')}: "
                    f"total={payload['kpis']['total_ausentismos']}, "
                    f"justificados={payload['kpis']['justificados']}, "
                    f"injustificados={payload['kpis']['injustificados']}."
                )

            elif capability_id in {
                "attendance.unjustified.table.v1",
                "attendance.unjustified.table_with_personal.v1",
            }:
                needs_personal_join = capability_id.endswith("table_with_personal.v1") or self._message_requests_personal_join(message)
                if not needs_personal_join and memory_hints.get("supervisor"):
                    needs_personal_join = True
                    memory_hints_used.append(
                        {
                            "memory_key": "attendance.supervisor",
                            "memory_value": memory_hints.get("supervisor"),
                            "reason": "join_personal_enabled_from_memory_hint",
                        }
                    )
                detail = _measure_tool(
                    "attendance_get_unjustified_with_personal"
                    if needs_personal_join
                    else "attendance_get_unjustified_table",
                    self.tool.get_unjustified_table,
                    period=period,
                    include_personal=needs_personal_join,
                    personal_status=personal_status,
                    limit=150,
                )
                used_tools.append(
                    "get_attendance_unjustified_with_personal"
                    if needs_personal_join
                    else "get_attendance_unjustified_table"
                )
                source_rows = list(detail.get("rows") or [])
                rows = [
                    {k: v for k, v in row.items() if k != "personal_match"}
                    for row in source_rows
                ]
                payload["table"] = {
                    "columns": list(rows[0].keys()) if rows else [],
                    "rows": rows,
                    "rowcount": len(rows),
                }
                if not rows:
                    reply = (
                        "No se encontraron ausentismos injustificados entre "
                        f"{detail.get('periodo_inicio')} y {detail.get('periodo_fin')}."
                    )
                else:
                    reply = (
                        "Tabla de ausentismos injustificados del periodo "
                        f"{detail.get('periodo_inicio')} al {detail.get('periodo_fin')} "
                        f"({len(rows)} filas):\n\n{self._format_rows_table(rows)}"
                    )

                unmatched_personal = int(detail.get("unmatched_personal") or 0)
                if unmatched_personal > 0:
                    payload["insights"].append(
                        f"No fue posible homologar {unmatched_personal} registros con personal."
                    )

            elif capability_id in {
                "attendance.recurrence.grouped.v1",
                "attendance.recurrence.itemized.v1",
            }:
                intent = "attendance_recurrence"
                needs_personal_join = True
                grouped = _measure_tool(
                    "attendance_get_recurrence_grouped",
                    self.tool.get_recurrence_grouped,
                    period=period,
                    threshold=2,
                    personal_status=personal_status,
                    limit=150,
                )
                used_tools.append("get_attendance_recurrent_unjustified_with_supervisor")
                wants_itemized = capability_id.endswith("itemized.v1")
                if capability_id.endswith("grouped.v1"):
                    if self._message_wants_itemized(message):
                        wants_itemized = True
                    elif memory_hints.get("recurrence_view") == "itemized" and not self._message_wants_grouped(message):
                        wants_itemized = True
                        memory_hints_used.append(
                            {
                                "memory_key": "attendance.recurrence.default_view",
                                "memory_value": "itemized",
                                "reason": "itemized_selected_from_business_hint",
                            }
                        )

                if wants_itemized:
                    itemized = _measure_tool(
                        "attendance_get_recurrence_itemized",
                        self.tool.get_recurrence_itemized,
                        period=period,
                        grouped_result=grouped,
                        personal_status=personal_status,
                        detail_limit=500,
                    )
                    used_tools.append("get_attendance_unjustified_with_personal")
                    rows_for_response = list(itemized.get("rows") or [])
                    payload["table"] = {
                        "columns": list(rows_for_response[0].keys()) if rows_for_response else [],
                        "rows": rows_for_response,
                        "rowcount": len(rows_for_response),
                    }
                    payload["kpis"] = {
                        "total_reincidentes": int(itemized.get("recurrent_count") or grouped.get("rowcount") or 0),
                        "umbral_reincidencia": int(itemized.get("threshold") or grouped.get("threshold") or 2),
                        "total_ausentismos_reincidentes": len(rows_for_response),
                    }
                    if not rows_for_response:
                        reply = (
                            "No se encontraron ausentismos dia a dia para reincidentes en el periodo "
                            f"{itemized.get('periodo_inicio')} a {itemized.get('periodo_fin')}."
                        )
                    else:
                        reply = (
                            "Detalle de ausentismos injustificados (dia a dia) de empleados reincidentes "
                            f"en la ventana {itemized.get('periodo_inicio')} a {itemized.get('periodo_fin')} "
                            f"(umbral >= {payload['kpis']['umbral_reincidencia']}), "
                            f"total_reincidentes={payload['kpis']['total_reincidentes']}:\n\n"
                            f"{self._format_rows_table(rows_for_response)}"
                        )
                else:
                    grouped_rows = list(grouped.get("rows_grouped") or [])
                    payload["table"] = {
                        "columns": list(grouped_rows[0].keys()) if grouped_rows else [],
                        "rows": grouped_rows,
                        "rowcount": len(grouped_rows),
                    }
                    payload["kpis"] = {
                        "total_reincidentes": int(grouped.get("rowcount") or len(grouped_rows)),
                        "umbral_reincidencia": int(grouped.get("threshold") or 2),
                    }
                    if not grouped_rows:
                        reply = (
                            "No se encontraron reincidentes injustificados entre "
                            f"{grouped.get('periodo_inicio')} y {grouped.get('periodo_fin')}."
                        )
                    else:
                        reply = (
                            "Reincidentes injustificados en la ventana "
                            f"{grouped.get('periodo_inicio')} a {grouped.get('periodo_fin')} "
                            f"(umbral >= {payload['kpis']['umbral_reincidencia']}), "
                            f"total_reincidentes={payload['kpis']['total_reincidentes']}:\n\n"
                            f"{self._format_rows_table(grouped_rows)}"
                        )
                        payload["insights"].append(
                            "Si quieres, puedo mostrarlo dia a dia (ausentismo por ausentismo)."
                        )
            else:
                return AttendanceHandleResult(
                    ok=False,
                    error=f"attendance capability no soportada: {capability_id}",
                    metadata={"capability_id": capability_id},
                )

            period_alternative_hint = self._build_period_alternative_hint(message=message, period=period)
            if period_alternative_hint:
                payload["insights"].append(period_alternative_hint)
                reply = f"{reply}\n\n{period_alternative_hint}" if reply else period_alternative_hint

            for hint in memory_hints_used:
                self._record_memory_hint_event(
                    observability=observability,
                    run_context=run_context,
                    sid=sid,
                    capability_id=capability_id,
                    hint=hint,
                )

            SessionMemoryStore.update_context(
                sid,
                {
                    "last_domain": "attendance",
                    "last_intent": intent,
                    "last_focus": focus,
                    "last_output_mode": response_output_mode,
                    "last_needs_database": True,
                    "last_personal_status": personal_status,
                    "last_selected_agent": "attendance_agent",
                    "last_period_start": period.start.isoformat(),
                    "last_period_end": period.end.isoformat(),
                },
            )
            SessionMemoryStore.append_turn(sid, message, reply)
            memory_status = SessionMemoryStore.status(sid)

            total_duration_ms = int((time.perf_counter() - started_at) * 1000)
            data_sources = {
                "attendance": {
                    "ok": True,
                    "attendance_table": self.tool.attendance_table,
                    "attendance_table_source": self.tool.attendance_table_source,
                    "personal_table": self.tool.personal_table,
                    "personal_table_source": self.tool.personal_table_source,
                },
                "ai_dictionary": {
                    "ok": True,
                    "source": "capability_handler",
                },
            }
            response = {
                "session_id": sid,
                "reply": reply,
                "orchestrator": {
                    "intent": intent,
                    "domain": "attendance",
                    "selected_agent": "attendance_agent",
                    "classifier_source": "capability_handler",
                    "needs_database": True,
                    "output_mode": response_output_mode,
                    "used_tools": used_tools,
                },
                "data": payload,
                "actions": actions,
                "data_sources": data_sources,
                "trace": trace,
                "memory": memory_status,
                "observability": {
                    "enabled": bool(getattr(observability, "enabled", True)),
                    "duration_ms": total_duration_ms,
                    "tool_latencies_ms": tool_latencies_ms,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "estimated_cost_usd": 0.0,
                },
                "active_nodes": self._resolve_active_nodes(
                    output_mode=response_output_mode,
                    used_tools=used_tools,
                ),
            }
            _push_trace(
                "attendance_capability_execution",
                "ok",
                {
                    "capability_id": capability_id,
                    "rowcount": int(payload.get("table", {}).get("rowcount") or 0),
                    "memory_hints_used": len(memory_hints_used),
                },
                self._resolve_active_nodes(output_mode=response_output_mode, used_tools=used_tools),
            )

            return AttendanceHandleResult(
                ok=True,
                response=response,
                metadata={
                    "memory_hints": memory_hints,
                    "memory_hints_used": memory_hints_used,
                    "capability_id": capability_id,
                    "policy_tags": list(planned_capability.get("policy_tags") or []),
                },
            )
        except Exception as exc:
            logger.exception("Attendance capability handler failed")
            return AttendanceHandleResult(
                ok=False,
                error=str(exc),
                metadata={"capability_id": capability_id},
            )

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = (text or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    def _resolve_period_for_attendance(self, *, message: str, session_context: dict[str, Any]) -> AttendancePeriod:
        period = resolve_period_from_text(message)
        label = str(period.get("label") or "hoy")
        source = "rules"
        start = period.get("start")
        end = period.get("end")

        normalized = self._normalize_text(message)
        if _YES_FOLLOW_UP_RE.match(normalized) and not self._has_explicit_period(message):
            prev_start = str(session_context.get("last_period_start") or "").strip()
            prev_end = str(session_context.get("last_period_end") or "").strip()
            if prev_start and prev_end:
                try:
                    start = date.fromisoformat(prev_start)
                    end = date.fromisoformat(prev_end)
                    label = "contexto_previo"
                    source = "context"
                except ValueError:
                    pass

        if not isinstance(start, date) or not isinstance(end, date):
            today = date.today()
            start = today
            end = today
            label = "hoy"
            source = "rules"

        return AttendancePeriod(start=start, end=end, label=label, source=source)

    def _extract_memory_hints(self, memory_context: dict[str, Any] | None) -> dict[str, Any]:
        context = dict(memory_context or {})
        user_memory = list(context.get("user_memory") or [])
        business_memory = list(context.get("business_memory") or [])

        hints = {
            "output_mode": None,
            "personal_status": None,
            "recurrence_view": None,
            "team": None,
            "supervisor": None,
        }

        for row in user_memory:
            key = str(row.get("memory_key") or "").strip().lower()
            value = self._coerce_memory_value(row.get("memory_value"))
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
            value = self._coerce_memory_value(row.get("memory_value"))
            if key == "attendance.recurrence.default_view" and value:
                hints["recurrence_view"] = value
            elif key == "attendance.default.personal_status" and value and not hints.get("personal_status"):
                hints["personal_status"] = value

        return hints

    @staticmethod
    def _coerce_memory_value(value: Any) -> str | None:
        if isinstance(value, dict):
            if "value" in value:
                raw = value.get("value")
            else:
                raw = next(iter(value.values()), None)
        else:
            raw = value
        text = str(raw or "").strip().lower()
        return text or None

    def _resolve_personal_status(
        self,
        *,
        message: str,
        session_context: dict[str, Any],
        hints: dict[str, Any],
        used: list[dict[str, Any]],
    ) -> str:
        normalized = self._normalize_text(message)
        if "inactivo" in normalized or "inactivos" in normalized:
            return "inactivos"
        if "activo" in normalized or "activos" in normalized:
            return "activos"

        hint_value = str(hints.get("personal_status") or "").strip().lower()
        if hint_value in {"all", "activos", "inactivos"}:
            used.append(
                {
                    "memory_key": "attendance.personal_status",
                    "memory_value": hint_value,
                    "reason": "personal_status_loaded_from_user_memory",
                }
            )
            return hint_value

        if _YES_FOLLOW_UP_RE.match(normalized):
            previous = str(session_context.get("last_personal_status") or "").strip().lower()
            if previous in {"all", "activos", "inactivos"}:
                return previous

        return "all"

    def _message_requests_personal_join(self, message: str) -> bool:
        normalized = self._normalize_text(message)
        return any(token in normalized for token in self._PERSONAL_TOKENS)

    def _message_wants_itemized(self, message: str) -> bool:
        normalized = self._normalize_text(message)
        return any(token in normalized for token in self._ITEMIZED_TOKENS)

    def _message_wants_grouped(self, message: str) -> bool:
        normalized = self._normalize_text(message)
        return any(token in normalized for token in self._GROUPED_TOKENS)

    def _has_explicit_period(self, text: str) -> bool:
        msg = self._normalize_text(text)
        if re.search(r"\d{4}-\d{2}-\d{2}", msg):
            return True
        if re.search(r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b", msg):
            return True
        return any(token in msg for token in ("hoy", "ayer", "ultima semana", "ultimos", "mes", "anio", "rango"))

    @staticmethod
    def _format_rows_table(rows: list[dict[str, Any]], max_rows: int = 20) -> str:
        if not rows:
            return "(sin resultados)"
        preview_rows = rows[:max_rows]
        columns = list(preview_rows[0].keys())
        header = " | ".join(columns)
        separator = " | ".join(["---"] * len(columns))
        body = []
        for row in preview_rows:
            body.append(" | ".join(str(row.get(col, "")) for col in columns))
        suffix = f"\n... ({len(rows) - max_rows} filas adicionales)" if len(rows) > max_rows else ""
        return f"{header}\n{separator}\n" + "\n".join(body) + suffix

    def _build_period_alternative_hint(self, *, message: str, period: AttendancePeriod) -> str | None:
        normalized = self._normalize_text(message)
        label = str(period.label or "").lower()
        today = date.today()

        if "mes anterior" in normalized or "mes pasado" in normalized or label == "mes_anterior":
            rolling_start = today - timedelta(days=29)
            rolling_end = today
            return (
                "Si quieres, tambien puedo mostrarlo como ultimo mes movil de 30 dias "
                f"({rolling_start.isoformat()} a {rolling_end.isoformat()}). "
                "Responde: si, ultimo mes."
            )

        if re.search(r"\bultim[oa]s?\s+mes\b", normalized) or label == "ultimo_mes_30_dias":
            first_current = today.replace(day=1)
            prev_end = first_current - timedelta(days=1)
            prev_start = prev_end.replace(day=1)
            return (
                "Si prefieres, tambien puedo mostrarlo como mes anterior calendario "
                f"({prev_start.isoformat()} a {prev_end.isoformat()}). "
                "Responde: si, mes anterior."
            )

        return None

    @staticmethod
    def _resolve_active_nodes(*, output_mode: str, used_tools: list[str]) -> list[str]:
        active = {"q", "gpt", "route", "aus", "result", "audit"}
        if output_mode in {"table", "list"}:
            active.update({"join", "check"})
        if any("personal" in tool for tool in used_tools):
            active.update({"personal", "join"})
        if any("recurrence" in tool for tool in used_tools):
            active.add("rules")
        return sorted(active)

    @staticmethod
    def _record_memory_hint_event(
        *,
        observability,
        run_context: RunContext,
        sid: str,
        capability_id: str,
        hint: dict[str, Any],
    ) -> None:
        if observability is None or not hasattr(observability, "record_event"):
            return
        observability.record_event(
            event_type="attendance_memory_hint_used",
            source="AttendanceHandler",
            meta={
                "run_id": run_context.run_id,
                "trace_id": run_context.trace_id,
                "session_id": sid,
                "capability_id": capability_id,
                "memory_key": hint.get("memory_key"),
                "memory_value": hint.get("memory_value"),
                "reason": hint.get("reason"),
            },
        )
