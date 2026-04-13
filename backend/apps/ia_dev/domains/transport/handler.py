from __future__ import annotations

import logging
import re
import time
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from apps.ia_dev.TOOLS.business.transport_business_tool import (
    TransportBusinessTool,
    TransportPeriod,
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
class TransportHandleResult:
    ok: bool
    response: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


class TransportHandler:
    def __init__(self, *, tool: TransportBusinessTool | None = None):
        self.tool = tool or TransportBusinessTool()

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
    ) -> TransportHandleResult:
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
                    "active_nodes": active_nodes or ["q", "gpt", "route", "transport", "result"],
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
            if capability_id != "transport.departures.summary.v1":
                return TransportHandleResult(
                    ok=False,
                    error=f"transport capability no soportada: {capability_id}",
                    metadata={"capability_id": capability_id},
                )

            source_status = _measure_tool(
                "transport_source_status",
                self.tool.source_status,
            )
            session_context = SessionMemoryStore.get_context(sid)
            memory_hints = self._extract_memory_hints(memory_context)
            memory_hints_used: list[dict[str, Any]] = []
            period = self._resolve_target_day(
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
                    "day": period.day.isoformat(),
                },
                ["q", "route", "rules", "transport"],
            )

            if not bool(source_status.get("configured")):
                reply = (
                    "No cuento con una base de datos de transporte configurada para responder "
                    "cuantos vehiculos salieron hoy. Por favor contacta al equipo de desarrollo."
                )
                actions.append(
                    {
                        "id": "create_ticket_transport_source",
                        "type": "create_ticket",
                        "label": "Crear ticket para configurar transporte",
                        "payload": {
                            "category": "missing_data_source",
                            "title": "Configurar fuente de transporte en IA DEV",
                            "description": (
                                "Se solicito conteo de vehiculos de hoy, pero no hay "
                                "IA_DEV_TRANSPORT_TABLE configurada."
                            ),
                        },
                    }
                )
                _push_trace(
                    "tool_execution",
                    "warning",
                    {
                        "tool": "get_transport_departures_summary",
                        "reason": "missing_data_source",
                    },
                    self._resolve_active_nodes(used_tools=used_tools, has_actions=True),
                )
            else:
                try:
                    summary = _measure_tool(
                        "get_transport_departures_summary",
                        self.tool.get_departures_summary,
                        period=period,
                    )
                    used_tools.append("get_transport_departures_summary")
                    total_salidas = int(summary.get("total_salidas") or 0)
                    fecha = str(summary.get("fecha") or period.day.isoformat())
                    payload["kpis"] = {
                        "total_salidas": total_salidas,
                    }
                    payload["table"] = {
                        "columns": ["fecha", "total_salidas"],
                        "rows": [{"fecha": fecha, "total_salidas": total_salidas}],
                        "rowcount": 1,
                    }
                    payload["series"] = [total_salidas]
                    payload["labels"] = [fecha]
                    reply = (
                        f"Para la fecha {fecha} se registran "
                        f"{total_salidas} salidas de vehiculos."
                    )
                    _push_trace(
                        "tool_execution",
                        "ok",
                        {
                            "tools": used_tools,
                            "rowcount": 1,
                        },
                        self._resolve_active_nodes(used_tools=used_tools, has_actions=False),
                    )
                except Exception as exc:
                    reply = (
                        "No fue posible consultar transporte con la fuente configurada. "
                        "Contacta al equipo de desarrollo para revisar estructura de tabla/columnas."
                    )
                    actions.append(
                        {
                            "id": "create_ticket_transport_query_error",
                            "type": "create_ticket",
                            "label": "Crear ticket por error de consulta transporte",
                            "payload": {
                                "category": "tool_query_error",
                                "title": "Error consultando transporte en IA DEV",
                                "description": str(exc),
                            },
                        }
                    )
                    _push_trace(
                        "tool_execution",
                        "error",
                        {
                            "tools": used_tools,
                            "error": str(exc),
                        },
                        self._resolve_active_nodes(used_tools=used_tools, has_actions=True),
                    )

            for hint in memory_hints_used:
                self._record_memory_hint_event(
                    observability=observability,
                    run_context=run_context,
                    sid=sid,
                    capability_id=capability_id,
                    hint=hint,
                )

            last_date = period.day.isoformat()
            SessionMemoryStore.update_context(
                sid,
                {
                    "last_domain": "transport",
                    "last_intent": "transport_query",
                    "last_focus": "departures",
                    "last_output_mode": "summary",
                    "last_needs_database": True,
                    "last_selected_agent": "transport_agent",
                    "last_transport_date": last_date,
                    "last_period_start": last_date,
                    "last_period_end": last_date,
                },
            )
            SessionMemoryStore.append_turn(sid, message, reply)
            memory_status = SessionMemoryStore.status(sid)

            total_duration_ms = int((time.perf_counter() - started_at) * 1000)
            response = {
                "session_id": sid,
                "reply": reply,
                "orchestrator": {
                    "intent": "transport_query",
                    "domain": "transport",
                    "selected_agent": "transport_agent",
                    "classifier_source": "capability_handler",
                    "needs_database": True,
                    "output_mode": "summary",
                    "used_tools": used_tools,
                },
                "data": payload,
                "actions": actions,
                "data_sources": {
                    "transport": source_status,
                    "ai_dictionary": {
                        "ok": True,
                        "source": "capability_handler",
                    },
                },
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
                    used_tools=used_tools,
                    has_actions=bool(actions),
                ),
            }

            return TransportHandleResult(
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
            logger.exception("Transport capability handler failed")
            return TransportHandleResult(
                ok=False,
                error=str(exc),
                metadata={"capability_id": capability_id},
            )

    def _resolve_target_day(
        self,
        *,
        message: str,
        session_context: dict[str, Any],
        hints: dict[str, Any],
        used: list[dict[str, Any]],
    ) -> TransportPeriod:
        normalized = self._normalize_text(message)
        has_explicit_period = self._has_explicit_period(message)
        period = resolve_period_from_text(message)
        start = period.get("start")
        end = period.get("end")
        day = end if isinstance(end, date) else date.today()
        label = str(period.get("label") or "hoy")
        source = "rules"

        if _YES_FOLLOW_UP_RE.match(normalized) and not has_explicit_period:
            context_day = str(session_context.get("last_transport_date") or "").strip()
            if context_day:
                try:
                    day = date.fromisoformat(context_day)
                    label = "contexto_previo"
                    source = "context"
                except ValueError:
                    pass

        if source == "rules" and not has_explicit_period:
            hint_label = str(hints.get("default_period_label") or "").strip().lower()
            if hint_label in {"hoy", "today"}:
                day = date.today()
                label = "hoy"
                source = "memory_hint"
                used.append(
                    {
                        "memory_key": "transport.default_period_label",
                        "memory_value": "hoy",
                        "reason": "default_period_loaded_from_memory_hint",
                    }
                )
            elif hint_label in {"ayer", "yesterday"}:
                day = date.today() - timedelta(days=1)
                label = "ayer"
                source = "memory_hint"
                used.append(
                    {
                        "memory_key": "transport.default_period_label",
                        "memory_value": "ayer",
                        "reason": "default_period_loaded_from_memory_hint",
                    }
                )

        if not isinstance(start, date):
            start = day
        if not isinstance(end, date):
            end = day
        if day < start or day > end:
            day = end

        return TransportPeriod(day=day, label=label, source=source)

    def _extract_memory_hints(self, memory_context: dict[str, Any] | None) -> dict[str, Any]:
        context = dict(memory_context or {})
        user_memory = list(context.get("user_memory") or [])
        business_memory = list(context.get("business_memory") or [])

        hints = {
            "default_period_label": None,
            "output_mode": None,
        }

        for row in user_memory:
            key = str(row.get("memory_key") or "").strip().lower()
            value = self._coerce_memory_value(row.get("memory_value"))
            if key == "transport.default_period_label" and value:
                hints["default_period_label"] = value
            elif key == "transport.output_mode" and value:
                hints["output_mode"] = value

        for row in business_memory:
            key = str(row.get("memory_key") or "").strip().lower()
            value = self._coerce_memory_value(row.get("memory_value"))
            if key == "transport.default_period_label" and value and not hints.get("default_period_label"):
                hints["default_period_label"] = value

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

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = (text or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    def _has_explicit_period(self, text: str) -> bool:
        msg = self._normalize_text(text)
        if re.search(r"\d{4}-\d{2}-\d{2}", msg):
            return True
        if re.search(r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b", msg):
            return True
        return any(
            token in msg
            for token in (
                "hoy",
                "ayer",
                "esta semana",
                "semana actual",
                "semana pasada",
                "semana anterior",
                "ultima semana",
                "ultimos",
                "mes",
                "anio",
                "rango",
            )
        )

    @staticmethod
    def _resolve_active_nodes(*, used_tools: list[str], has_actions: bool) -> list[str]:
        active = {"q", "gpt", "route", "transport", "result", "audit"}
        if "get_transport_departures_summary" in used_tools:
            active.update({"join", "rules", "check"})
        if has_actions:
            active.update({"alert", "audit"})
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
            event_type="transport_memory_hint_used",
            source="TransportHandler",
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
