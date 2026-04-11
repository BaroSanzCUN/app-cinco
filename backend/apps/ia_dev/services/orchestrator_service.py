import json
import logging
import os
import re
import threading
import time
import unicodedata
from datetime import date, datetime, timedelta

from .observability_service import ObservabilityService
from .dictionary_tool_service import DictionaryToolService
from .intent_service import IntentClassifierService
from .knowledge_governance_service import KnowledgeGovernanceService
from .memory_service import SessionMemoryStore
from .period_service import resolve_period_from_text
from .tool_attendance_service import AttendanceToolService
from .tool_transport_service import TransportToolService


logger = logging.getLogger(__name__)
_YES_FOLLOW_UP_RE = re.compile(
    r"^((si)([,! ]+por favor)?|ok|dale|perfecto|claro|adelante|continua|por favor)[.! ]*$",
    re.IGNORECASE,
)


class IADevOrchestratorService:
    def __init__(self):
        self.intent_classifier = IntentClassifierService()
        self.attendance_tool = AttendanceToolService()
        self.dictionary_tool = DictionaryToolService()
        self.knowledge_governance = KnowledgeGovernanceService()
        self.observability = ObservabilityService()
        self.transport_tool = TransportToolService()
        self.enable_openai_general = os.getenv(
            "IA_DEV_USE_OPENAI_GENERAL", "1"
        ).strip().lower() in ("1", "true", "yes", "on")
        self.general_model = os.getenv(
            "IA_DEV_GENERAL_MODEL", os.getenv("IA_DEV_MODEL", "gpt-5-nano")
        )
        self.enable_openai_period = os.getenv(
            "IA_DEV_USE_OPENAI_PERIOD", "1"
        ).strip().lower() in ("1", "true", "yes", "on")
        self.period_model = os.getenv(
            "IA_DEV_PERIOD_MODEL",
            os.getenv("IA_DEV_INTENT_MODEL", self.general_model),
        )
        self.enable_openai_followups = os.getenv(
            "IA_DEV_USE_OPENAI_FOLLOWUPS", "1"
        ).strip().lower() in ("1", "true", "yes", "on")
        self.followup_model = os.getenv(
            "IA_DEV_FOLLOWUP_MODEL",
            self.general_model,
        )
        self._last_openai_usage: dict | None = None
        self._delegate_state = threading.local()
        self._delegate_state.skip = False
        self._chat_application_service = None
        try:
            from apps.ia_dev.application.orchestration.chat_application_service import (
                ChatApplicationService,
            )

            self._chat_application_service = ChatApplicationService()
        except Exception:
            logger.exception(
                "No se pudo inicializar ChatApplicationService, se mantiene orchestrator legacy."
            )

    @staticmethod
    def _get_openai_api_key() -> str:
        return (
            os.getenv("OPENAI_API_KEY") or os.getenv("IA_DEV_OPENAI_API_KEY") or ""
        ).strip()

    def run(
        self,
        message: str,
        session_id: str | None = None,
        reset_memory: bool = False,
        actor_user_key: str | None = None,
    ) -> dict:
        if self._chat_application_service is not None and not self._is_delegate_skipped():
            try:
                return self._chat_application_service.run(
                    message=message,
                    session_id=session_id,
                    reset_memory=reset_memory,
                    legacy_runner=self.run_legacy,
                    observability=self.observability,
                    actor_user_key=actor_user_key,
                )
            except Exception:
                logger.exception(
                    "Fallo delegado ChatApplicationService, fallback a orquestador legacy."
                )

        started_at = time.perf_counter()
        tool_latencies_ms: dict[str, int] = {}
        self._last_openai_usage = None

        def _measure_tool(name: str, fn, *args, **kwargs):
            t0 = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                duration_ms = int((time.perf_counter() - t0) * 1000)
                tool_latencies_ms[name] = duration_ms
                self.observability.record_event(
                    event_type="tool_latency",
                    source=name,
                    duration_ms=duration_ms,
                    meta={"session_id": sid},
                )

        sid, _ = SessionMemoryStore.get_or_create(session_id)
        session_context = SessionMemoryStore.get_context(sid)
        recent_messages = SessionMemoryStore.get_recent_messages(sid, limit=8)

        if reset_memory:
            SessionMemoryStore.reset(sid)

        trace = []
        used_tools = []
        actions = []
        data_sources = {
            "ai_dictionary": {
                "ok": False,
                "table": None,
                "rows": 0,
            },
            "transport": {
                "ok": False,
                "configured": False,
                "table": None,
            },
            "knowledge_governance": {
                "mode": self.knowledge_governance.mode,
                "requires_auth": self.knowledge_governance.mode == "ceo",
            },
        }

        classification: dict = {
            "intent": "general_question",
            "domain": "general",
            "selected_agent": "analista_agent",
            "classifier_source": "rules",
            "needs_database": False,
            "output_mode": "summary",
        }
        domain = "general"
        needs_database = False
        output_mode = "summary"

        def push_trace(
            phase: str,
            status: str,
            detail,
            active_nodes: set[str] | None = None,
        ) -> None:
            trace.append(
                {
                    "phase": phase,
                    "status": status,
                    "at": datetime.utcnow().isoformat() + "Z",
                    "detail": detail,
                    "active_nodes": sorted(active_nodes or {"q", "gpt", "route"}),
                }
            )

        push_trace(
            "intake",
            "ok",
            "Message received by orchestrator",
            {"q", "gpt", "route"},
        )
        if recent_messages:
            push_trace(
                "memory_context",
                "ok",
                {
                    "recent_messages": len(recent_messages),
                    "has_context": bool(session_context),
                },
                {"q", "gpt", "route"},
            )

        transport_status = data_sources["transport"]
        probe_message = self._extract_period_probe_message(message)
        if probe_message:
            period_resolution = self.resolve_attendance_period(
                message=probe_message,
                session_id=sid,
            )
            resolved = period_resolution.get("resolved_period") or {}
            fallback = period_resolution.get("rules_fallback_period") or {}
            alternative_hint = period_resolution.get("alternative_hint")
            start_date = str(resolved.get("start_date") or "")
            end_date = str(resolved.get("end_date") or "")
            source = str(resolved.get("source") or "rules")

            reply_lines = [
                "Rango detectado para asistencia:",
                (
                    f"- {resolved.get('label', 'rango')} => "
                    f"{start_date or 'N/D'} a {end_date or 'N/D'} "
                    f"(source={source})"
                ),
                (
                    f"- Fallback por reglas => {fallback.get('start_date', 'N/D')} "
                    f"a {fallback.get('end_date', 'N/D')}"
                ),
            ]
            if alternative_hint:
                reply_lines.append(str(alternative_hint))
            reply_lines.append(
                "Siguiente paso sugerido: escribe "
                "\"Ejecuta esta consulta con ese rango en formato tabla\"."
            )
            reply = "\n".join(reply_lines)

            payload = {
                "kpis": {},
                "series": [],
                "labels": [],
                "insights": [
                    "Modo prueba de rango: no se ejecuto consulta SQL de ausentismo.",
                ],
                "table": {
                    "columns": [],
                    "rows": [],
                    "rowcount": 0,
                },
                "period_resolution": period_resolution,
            }

            if alternative_hint:
                payload["insights"].append(str(alternative_hint))

            push_trace(
                "period_probe",
                "ok",
                period_resolution,
                {"q", "gpt", "route", "meta", "result"},
            )

            if start_date and end_date:
                SessionMemoryStore.update_context(
                    sid,
                    {
                        "last_domain": "attendance",
                        "last_intent": "attendance_period_probe",
                        "last_focus": "unjustified",
                        "last_output_mode": "table",
                        "last_needs_database": True,
                        "last_personal_status": self._resolve_personal_status_filter(
                            message=probe_message,
                            session_context=session_context,
                        ),
                        "last_selected_agent": "attendance_agent",
                        "last_period_start": start_date,
                        "last_period_end": end_date,
                    },
                )

            SessionMemoryStore.append_turn(sid, message, reply)
            memory_status = SessionMemoryStore.status(sid)
            total_duration_ms = int((time.perf_counter() - started_at) * 1000)
            tokens_in = int((self._last_openai_usage or {}).get("tokens_in") or 0)
            tokens_out = int((self._last_openai_usage or {}).get("tokens_out") or 0)
            estimated_cost_usd = self._estimate_openai_cost(
                model=self.general_model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
            observability_payload = {
                "enabled": self.observability.enabled,
                "duration_ms": total_duration_ms,
                "tool_latencies_ms": tool_latencies_ms,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "estimated_cost_usd": estimated_cost_usd,
            }
            self.observability.record_event(
                event_type="orchestrator_run",
                source="IADevOrchestratorService",
                duration_ms=total_duration_ms,
                tokens_in=tokens_in or None,
                tokens_out=tokens_out or None,
                cost_usd=estimated_cost_usd or None,
                meta={
                    "session_id": sid,
                    "intent": "attendance_period_probe",
                    "domain": "attendance",
                    "output_mode": "summary",
                    "used_tools": used_tools,
                },
            )
            return {
                "session_id": sid,
                "reply": reply,
                "orchestrator": {
                    "intent": "attendance_period_probe",
                    "domain": "attendance",
                    "selected_agent": "attendance_agent",
                    "classifier_source": "period_probe",
                    "needs_database": False,
                    "output_mode": "summary",
                    "used_tools": used_tools,
                },
                "data": payload,
                "actions": actions,
                "data_sources": data_sources,
                "trace": trace,
                "memory": memory_status,
                "observability": observability_payload,
                "active_nodes": self._resolve_active_nodes(
                    domain="attendance",
                    selected_agent="attendance_agent",
                    used_tools=used_tools,
                    has_actions=bool(actions),
                    needs_database=False,
                ),
            }

        classification = self.intent_classifier.classify(message)
        classification = self._apply_followup_overrides(
            message=message,
            classification=classification,
            session_context=session_context,
        )
        push_trace(
            "classification",
            "ok",
            classification,
            {"q", "gpt", "route"},
        )

        payload = {
            "kpis": {},
            "series": [],
            "labels": [],
            "insights": [],
            "table": {
                "columns": [],
                "rows": [],
                "rowcount": 0,
            },
        }

        reply = (
            "Consulta recibida. Puedo ayudarte con RRHH, asistencia, transporte, "
            "operaciones, viaticos, nomina y auditoria."
        )

        domain = classification.get("domain", "general")
        needs_database = bool(classification.get("needs_database"))
        output_mode = str(classification.get("output_mode", "summary"))
        needs_personal_join = bool(classification.get("needs_personal_join"))
        focus = str(classification.get("focus", "all"))
        intent = str(classification.get("intent", "general_question"))
        dictionary_context = None

        if needs_database:
            try:
                dictionary_status = _measure_tool(
                    "check_ai_dictionary_connection",
                    self.dictionary_tool.check_connection,
                )
                data_sources["ai_dictionary"] = dictionary_status
                used_tools.append("check_ai_dictionary_connection")
                push_trace(
                    "data_source_check",
                    "ok",
                    {"ai_dictionary": dictionary_status},
                    {"q", "gpt", "route", "meta"},
                )
                try:
                    dictionary_snapshot = _measure_tool(
                        "get_ai_dictionary_snapshot",
                        self.dictionary_tool.get_dictionary_snapshot,
                    )
                    data_sources["ai_dictionary"]["snapshot"] = dictionary_snapshot
                    used_tools.append("get_ai_dictionary_snapshot")
                    push_trace(
                        "dictionary_validation",
                        "ok",
                        dictionary_snapshot,
                        {"q", "gpt", "route", "meta"},
                    )
                except Exception as snapshot_exc:
                    push_trace(
                        "dictionary_validation",
                        "warning",
                        {"error": str(snapshot_exc)},
                        {"q", "gpt", "route", "meta"},
                    )
            except Exception as exc:
                push_trace(
                    "data_source_check",
                    "error",
                    {"ai_dictionary_error": str(exc)},
                    {"q", "gpt", "route", "meta"},
                )

            if data_sources.get("ai_dictionary", {}).get("ok"):
                try:
                    dictionary_context = _measure_tool(
                        "get_ai_dictionary_context",
                        self.dictionary_tool.get_domain_context,
                        domain,
                    )
                    used_tools.append("get_ai_dictionary_context")
                    push_trace(
                        "dictionary_context",
                        "ok",
                        {
                            "domain": dictionary_context.get("domain", {}),
                            "tables": [t.get("table_name") for t in dictionary_context.get("tables", [])],
                            "fields": [f.get("column_name") for f in dictionary_context.get("fields", [])][:12],
                            "rules": [r.get("codigo") for r in dictionary_context.get("rules", [])],
                            "synonyms": [s.get("sinonimo") for s in dictionary_context.get("synonyms", [])][:12],
                        },
                        {"q", "gpt", "route", "meta"},
                    )
                except Exception as context_exc:
                    push_trace(
                        "dictionary_context",
                        "warning",
                        {"error": str(context_exc), "domain": domain},
                        {"q", "gpt", "route", "meta"},
                    )

            if domain == "transport":
                transport_status = _measure_tool(
                    "transport_source_status",
                    self.transport_tool.source_status,
                )
                data_sources["transport"] = transport_status
                push_trace(
                    "data_source_check",
                    "ok" if transport_status.get("ok") else "warning",
                    {"transport": transport_status},
                    {"q", "gpt", "route", "meta", "transport"},
                )

        push_trace(
            "route_decision",
            "ok",
            {
                "needs_database": needs_database,
                "domain": domain,
                "selected_agent": classification.get("selected_agent"),
                "output_mode": output_mode,
            },
            self._resolve_active_nodes(
                domain=domain,
                selected_agent=classification.get("selected_agent"),
                used_tools=used_tools,
                has_actions=bool(actions),
                needs_database=needs_database,
            ),
        )

        if intent == "knowledge_change_request":
            proposal_result = self.knowledge_governance.create_proposal_from_message(
                message=message,
                session_id=sid,
                requested_by=str(classification.get("selected_agent") or "analista_agent"),
            )
            used_tools.append("knowledge_governance_create_proposal")
            data_sources["knowledge_governance"]["last_result"] = {
                "ok": bool(proposal_result.get("ok")),
                "requires_auth": bool(proposal_result.get("requires_auth")),
                "applied": bool(proposal_result.get("applied")),
            }

            proposal = proposal_result.get("proposal") or {}
            proposal_id = str(proposal.get("proposal_id") or "")

            if not proposal_result.get("ok"):
                reply = (
                    "No fue posible crear la propuesta de conocimiento en este momento. "
                    f"Detalle: {proposal_result.get('error', 'error no especificado')}"
                )
                push_trace(
                    "knowledge_governance",
                    "error",
                    proposal_result,
                    self._resolve_active_nodes(
                        domain=domain,
                        selected_agent=classification.get("selected_agent"),
                        used_tools=used_tools,
                        has_actions=bool(actions),
                        needs_database=needs_database,
                    ),
                )
            elif proposal_result.get("requires_auth"):
                reply = (
                    f"Se creó la propuesta {proposal_id} y quedó pendiente de aprobación del CEO.\n"
                    "Para aplicarla usa el endpoint: POST /ia-dev/knowledge/proposals/approve/ "
                    "con `proposal_id` y `auth_key`."
                )
                payload["insights"].append(
                    f"Propuesta {proposal_id} en estado pendiente (modo={self.knowledge_governance.mode})."
                )
                if proposal.get("similar_rules"):
                    payload["insights"].append(
                        "Reglas similares detectadas: "
                        + ", ".join(
                            str(item.get("codigo", ""))
                            for item in proposal.get("similar_rules", [])[:4]
                            if item.get("codigo")
                        )
                    )
                push_trace(
                    "knowledge_governance",
                    "warning",
                    {
                        "proposal_id": proposal_id,
                        "status": proposal.get("status"),
                        "requires_auth": True,
                    },
                    self._resolve_active_nodes(
                        domain=domain,
                        selected_agent=classification.get("selected_agent"),
                        used_tools=used_tools,
                        has_actions=bool(actions),
                        needs_database=needs_database,
                    ),
                )
            else:
                applied = proposal_result.get("apply_result") or {}
                persistence = applied.get("persistence") or {}
                reply = (
                    f"Propuesta {proposal_id} aplicada correctamente bajo modo "
                    f"{self.knowledge_governance.mode}.\n"
                    f"Resultado: {persistence.get('message', 'regla persistida en ai_dictionary')}"
                )
                payload["insights"].append(
                    f"Autoevolución aplicada: propuesta {proposal_id}."
                )
                push_trace(
                    "knowledge_governance",
                    "ok",
                    {
                        "proposal_id": proposal_id,
                        "status": "applied",
                        "persistence": persistence,
                    },
                    self._resolve_active_nodes(
                        domain=domain,
                        selected_agent=classification.get("selected_agent"),
                        used_tools=used_tools,
                        has_actions=bool(actions),
                        needs_database=needs_database,
                    ),
                )

        elif domain == "attendance" and needs_database:
            period = self._resolve_period_for_attendance(message, session_context, recent_messages)
            personal_status = self._resolve_personal_status_filter(
                message=message,
                session_context=session_context,
            )
            push_trace(
                "period_resolver",
                "ok",
                {
                    **period,
                    "personal_status_filter": personal_status,
                },
                self._resolve_active_nodes(
                    domain=domain,
                    selected_agent=classification.get("selected_agent"),
                    used_tools=used_tools,
                    has_actions=bool(actions),
                    needs_database=needs_database,
                ),
            )

            try:
                if output_mode in ("table", "list"):
                    if intent == "attendance_recurrence":
                        wants_itemized = self._wants_itemized_absence_view(message)
                        recurrence = _measure_tool(
                            "get_attendance_recurrent_unjustified_with_supervisor",
                            self.attendance_tool.get_recurrent_unjustified_with_supervisor,
                            period["start"],
                            period["end"],
                            threshold=2,
                            limit=150,
                            personal_status=personal_status,
                        )
                        used_tools.append("get_attendance_recurrent_unjustified_with_supervisor")
                        grouped_source_rows = list(recurrence.get("rows", []) or [])
                        grouped_rows = self._shape_recurrence_grouped_rows(grouped_source_rows)
                        rows_for_response = grouped_rows
                        table_title = "Reincidentes injustificados"
                        if wants_itemized and grouped_source_rows:
                            recurrent_ids = {
                                self._normalize_identifier(row.get("cedula"))
                                for row in grouped_source_rows
                            }
                            detail = _measure_tool(
                                "get_attendance_unjustified_with_personal",
                                self.attendance_tool.get_unjustified_with_personal,
                                period["start"],
                                period["end"],
                                limit=500,
                                personal_status=personal_status,
                            )
                            used_tools.append("get_attendance_unjustified_with_personal")
                            detail_rows = list(detail.get("rows", []) or [])
                            rows_for_response = []
                            for item in detail_rows:
                                if self._normalize_identifier(item.get("cedula")) not in recurrent_ids:
                                    continue
                                rows_for_response.append(
                                    {k: v for k, v in item.items() if k != "personal_match"}
                                )
                            table_title = (
                                "Detalle de ausentismos injustificados (dia a dia) de empleados reincidentes"
                            )
                        payload["table"] = {
                            "columns": list(rows_for_response[0].keys()) if rows_for_response else [],
                            "rows": rows_for_response,
                            "rowcount": len(rows_for_response),
                        }
                        payload["kpis"] = {
                            "total_reincidentes": int(recurrence.get("rowcount") or len(grouped_source_rows)),
                            "umbral_reincidencia": int(recurrence.get("threshold") or 2),
                        }
                        if wants_itemized and grouped_source_rows:
                            payload["kpis"]["total_ausentismos_reincidentes"] = len(rows_for_response)

                        if not grouped_source_rows:
                            reply = (
                                f"No se encontraron reincidentes injustificados entre "
                                f"{recurrence['periodo_inicio']} y {recurrence['periodo_fin']}."
                            )
                        else:
                            preview = self._format_rows_table(rows_for_response)
                            reply = (
                                f"{table_title} en la ventana {recurrence['periodo_inicio']} "
                                f"a {recurrence['periodo_fin']} (umbral >= {recurrence['threshold']}), "
                                f"total_reincidentes={payload['kpis']['total_reincidentes']}:\n\n{preview}"
                            )
                            if not wants_itemized:
                                follow_up = _measure_tool(
                                    "generate_contextual_followup",
                                    self._generate_contextual_followup,
                                    message=message,
                                    base_reply=reply,
                                    domain=domain,
                                    intent=intent,
                                    rowcount=int(payload["table"].get("rowcount") or 0),
                                    recent_messages=recent_messages,
                                )
                                used_tools.append("generate_contextual_followup")
                                if follow_up:
                                    payload["insights"].append(follow_up)
                                    reply = f"{reply}\n\n{follow_up}"
                    elif focus in ("unjustified", "missing_personal"):
                        if needs_personal_join:
                            try:
                                detail = _measure_tool(
                                    "get_attendance_unjustified_with_personal",
                                    self.attendance_tool.get_unjustified_with_personal,
                                    period["start"],
                                    period["end"],
                                    limit=150,
                                    personal_status=personal_status,
                                )
                                used_tools.append("get_attendance_unjustified_with_personal")
                            except Exception as join_exc:
                                detail = _measure_tool(
                                    "get_attendance_unjustified_table",
                                    self.attendance_tool.get_unjustified_table,
                                    period["start"],
                                    period["end"],
                                    limit=150,
                                )
                                used_tools.append("get_attendance_unjustified_table")
                                actions.append(
                                    {
                                        "id": "create_ticket_personal_join_source",
                                        "type": "create_ticket",
                                        "label": "Crear ticket para ajustar join con personal",
                                        "payload": {
                                            "category": "missing_data_source",
                                            "title": "Ajustar fuente/estructura de personal en IA DEV",
                                            "description": str(join_exc),
                                        },
                                    }
                                )
                        else:
                            detail = _measure_tool(
                                "get_attendance_unjustified_table",
                                self.attendance_tool.get_unjustified_table,
                                period["start"],
                                period["end"],
                                limit=150,
                            )
                            used_tools.append("get_attendance_unjustified_table")

                        rows = list(detail.get("rows", []) or [])
                        if focus == "missing_personal":
                            rows = [row for row in rows if not bool(row.get("personal_match"))]
                        display_rows = [
                            {k: v for k, v in row.items() if k != "personal_match"}
                            for row in rows
                        ]
                        payload["table"] = {
                            "columns": list(display_rows[0].keys()) if display_rows else [],
                            "rows": display_rows,
                            "rowcount": len(display_rows),
                        }

                        if not display_rows:
                            if focus == "missing_personal":
                                reply = (
                                    "No se encontraron ausentismos injustificados sin homologacion "
                                    f"de personal entre {detail['periodo_inicio']} y {detail['periodo_fin']}."
                                )
                            else:
                                reply = (
                                    f"No se encontraron ausentismos injustificados entre "
                                    f"{detail['periodo_inicio']} y {detail['periodo_fin']}."
                                )
                        else:
                            preview = self._format_rows_table(display_rows)
                            if focus == "missing_personal":
                                reply = (
                                    "Tabla de ausentismos injustificados sin homologacion de personal "
                                    f"del periodo {detail['periodo_inicio']} al {detail['periodo_fin']} "
                                    f"({payload['table']['rowcount']} filas):\n\n{preview}"
                                )
                            else:
                                reply = (
                                    f"Tabla de ausentismos injustificados del periodo "
                                    f"{detail['periodo_inicio']} al {detail['periodo_fin']} "
                                    f"({payload['table']['rowcount']} filas):\n\n{preview}"
                                )
                        unmatched_personal = int(detail.get("unmatched_personal") or 0)
                        matched_personal = int(detail.get("matched_personal") or 0)
                        personal_table = str(detail.get("personal_table") or "N/D")
                        personal_table_source = str(detail.get("personal_table_source") or "env")
                        attendance_table = str(detail.get("attendance_table") or "N/D")
                        attendance_table_source = str(detail.get("attendance_table_source") or "env")
                        if unmatched_personal > 0:
                            diagnostic = (
                                "No fue posible homologar datos de personal para "
                                f"{unmatched_personal} de {payload['table']['rowcount']} filas "
                                f"(homologadas: {matched_personal})."
                            )
                            mapping_info = (
                                "Mapeo de tablas usado: "
                                f"personal={personal_table} ({personal_table_source}), "
                                f"asistencia={attendance_table} ({attendance_table_source})."
                            )
                            suggestion = (
                                "Sugerencia: consulta \"Mostrar cedulas sin homologar en personal\" "
                                "o \"Crear ticket para homologar personal\"."
                            )
                            payload["insights"].append(diagnostic)
                            payload["insights"].append(mapping_info)
                            payload["insights"].append(suggestion)
                            reply = f"{reply}\n\n{diagnostic}\n{mapping_info}\n{suggestion}"
                    else:
                        detail = _measure_tool(
                            "get_attendance_detail_with_personal",
                            self.attendance_tool.get_detail_with_personal,
                            period["start"],
                            period["end"],
                            limit=150,
                            personal_status=personal_status,
                        )
                        used_tools.append("get_attendance_detail_with_personal")
                        rows = detail.get("rows", [])
                        payload["table"] = {
                            "columns": list(rows[0].keys()) if rows else [],
                            "rows": rows,
                            "rowcount": int(detail.get("rowcount") or len(rows)),
                        }
                        if not rows:
                            reply = (
                                f"No se encontraron ausentismos para el periodo "
                                f"{detail['periodo_inicio']} al {detail['periodo_fin']}."
                            )
                        else:
                            preview = self._format_rows_table(rows)
                            reply = (
                                f"Detalle de ausentismos del periodo {detail['periodo_inicio']} "
                                f"al {detail['periodo_fin']} ({payload['table']['rowcount']} filas):\n\n{preview}"
                            )
                else:
                    summary = _measure_tool(
                        "get_attendance_summary",
                        self.attendance_tool.get_summary,
                        period["start"],
                        period["end"],
                    )
                    used_tools.append("get_attendance_summary")
                    payload["kpis"] = {
                        "total_ausentismos": summary["total_ausentismos"],
                        "justificados": summary["justificados"],
                        "injustificados": summary["injustificados"],
                    }
                    payload["insights"] = [
                        f"Periodo: {summary['periodo_inicio']} a {summary['periodo_fin']}",
                        "Puedes pedir tabla/lista por persona, supervisor, area o cargo.",
                    ]

                    reply = (
                        f"Resumen de ausentismo del periodo {summary['periodo_inicio']} al {summary['periodo_fin']}: "
                        f"total={summary['total_ausentismos']}, "
                        f"justificados={summary['justificados']}, "
                        f"injustificados={summary['injustificados']}."
                    )

                push_trace(
                    "tool_execution",
                    "ok",
                    {
                        "tools": used_tools,
                        "rowcount": payload["table"].get("rowcount", 0),
                    },
                    self._resolve_active_nodes(
                        domain=domain,
                        selected_agent=classification.get("selected_agent"),
                        used_tools=used_tools,
                        has_actions=bool(actions),
                        needs_database=needs_database,
                    ),
                )
                period_alternative_hint = self._build_period_alternative_hint(
                    message=message,
                    period=period,
                )
                if period_alternative_hint:
                    reply = f"{reply}\n\n{period_alternative_hint}"
                    payload["insights"].append(period_alternative_hint)
            except Exception as exc:
                push_trace(
                    "tool_execution",
                    "error",
                    {
                        "tools": used_tools,
                        "error": str(exc),
                    },
                    self._resolve_active_nodes(
                        domain=domain,
                        selected_agent=classification.get("selected_agent"),
                        used_tools=used_tools,
                        has_actions=bool(actions),
                        needs_database=needs_database,
                    ),
                )
                reply = (
                    "No fue posible consultar ausentismo en este momento. "
                    "Valida conexion, VPN y configuracion IA_DEV_ATTENDANCE_TABLE."
                )

        elif domain == "transport" and needs_database:
            if not transport_status.get("configured"):
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
                push_trace(
                    "tool_execution",
                    "warning",
                    {
                        "tool": "get_transport_departures_summary",
                        "reason": "missing_data_source",
                    },
                    self._resolve_active_nodes(
                        domain=domain,
                        selected_agent=classification.get("selected_agent"),
                        used_tools=used_tools,
                        has_actions=bool(actions),
                        needs_database=needs_database,
                    ),
                )
            else:
                try:
                    period = resolve_period_from_text(message)
                    summary = _measure_tool(
                        "get_transport_departures_summary",
                        self.transport_tool.get_departures_summary,
                        period["end"],
                    )
                    used_tools.append("get_transport_departures_summary")
                    payload["kpis"] = {
                        "total_salidas": summary["total_salidas"],
                    }
                    reply = (
                        f"Para la fecha {summary['fecha']} se registran "
                        f"{summary['total_salidas']} salidas de vehiculos."
                    )
                    push_trace(
                        "tool_execution",
                        "ok",
                        {
                            "tools": used_tools,
                            "rowcount": 0,
                        },
                        self._resolve_active_nodes(
                            domain=domain,
                            selected_agent=classification.get("selected_agent"),
                            used_tools=used_tools,
                            has_actions=bool(actions),
                            needs_database=needs_database,
                        ),
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
                    push_trace(
                        "tool_execution",
                        "error",
                        {
                            "tools": used_tools,
                            "error": str(exc),
                        },
                        self._resolve_active_nodes(
                            domain=domain,
                            selected_agent=classification.get("selected_agent"),
                            used_tools=used_tools,
                            has_actions=bool(actions),
                            needs_database=needs_database,
                        ),
                    )
        elif not needs_database:
            llm_reply = _measure_tool(
                "generate_general_reply",
                self._generate_general_reply,
                message=message,
                recent_messages=recent_messages,
            )
            if llm_reply:
                reply = llm_reply
                push_trace(
                    "general_generation",
                    "ok",
                    {"source": "openai", "model": self.general_model},
                    self._resolve_active_nodes(
                        domain=domain,
                        selected_agent=classification.get("selected_agent"),
                        used_tools=used_tools,
                        has_actions=bool(actions),
                        needs_database=needs_database,
                    ),
                )
            else:
                reason = "openai_unavailable_or_error"
                openai_api_key = self._get_openai_api_key()
                if not self.enable_openai_general:
                    reason = "openai_general_disabled"
                    reply = (
                        "La respuesta general con OpenAI esta desactivada en este entorno "
                        "(IA_DEV_USE_OPENAI_GENERAL=0)."
                    )
                elif not openai_api_key:
                    reason = "openai_api_key_missing"
                    reply = (
                        "Puedo responder consultas generales, pero en este entorno no esta "
                        "configurada OPENAI_API_KEY (o IA_DEV_OPENAI_API_KEY) en el backend."
                    )

                push_trace(
                    "general_generation",
                    "warning",
                    {"source": "fallback", "reason": reason},
                    self._resolve_active_nodes(
                        domain=domain,
                        selected_agent=classification.get("selected_agent"),
                        used_tools=used_tools,
                        has_actions=bool(actions),
                        needs_database=needs_database,
                    ),
                )

        if needs_database and dictionary_context:
            applied_tables = [t.get("table_name") for t in dictionary_context.get("tables", []) if t.get("table_name")]
            if applied_tables:
                payload["insights"].append(
                    f"Contexto ai_dictionary aplicado ({dictionary_context.get('domain', {}).get('code', 'N/A')}): "
                    + ", ".join(applied_tables[:4])
                )
            applied_rules = [r.get("codigo") for r in dictionary_context.get("rules", []) if r.get("codigo")]
            if applied_rules:
                payload["insights"].append(
                    "Reglas de referencia: " + ", ".join(applied_rules[:4])
                )

        push_trace(
            "response_preparation",
            "ok",
            {
                "reply_preview": (reply or "")[:220],
                "domain": domain,
                "needs_database": needs_database,
                "used_tools": used_tools,
                "dictionary_domain": (
                    dictionary_context.get("domain", {}).get("code")
                    if dictionary_context
                    else None
                ),
            },
            self._resolve_active_nodes(
                domain=domain,
                selected_agent=classification.get("selected_agent"),
                used_tools=used_tools,
                has_actions=bool(actions),
                needs_database=needs_database,
            ),
        )

        SessionMemoryStore.update_context(
            sid,
            {
                "last_domain": domain,
                "last_intent": intent,
                "last_focus": focus,
                "last_output_mode": output_mode,
                "last_needs_database": needs_database,
                "last_personal_status": (
                    self._resolve_personal_status_filter(
                        message=message,
                        session_context=session_context,
                    )
                    if domain == "attendance" and needs_database
                    else session_context.get("last_personal_status")
                ),
                "last_selected_agent": classification.get("selected_agent"),
                "last_period_start": (
                    period["start"].isoformat() if domain == "attendance" and needs_database else None
                ),
                "last_period_end": (
                    period["end"].isoformat() if domain == "attendance" and needs_database else None
                ),
            },
        )

        SessionMemoryStore.append_turn(sid, message, reply)
        memory_status = SessionMemoryStore.status(sid)
        total_duration_ms = int((time.perf_counter() - started_at) * 1000)
        tokens_in = int((self._last_openai_usage or {}).get("tokens_in") or 0)
        tokens_out = int((self._last_openai_usage or {}).get("tokens_out") or 0)
        estimated_cost_usd = self._estimate_openai_cost(
            model=self.general_model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
        )
        observability_payload = {
            "enabled": self.observability.enabled,
            "duration_ms": total_duration_ms,
            "tool_latencies_ms": tool_latencies_ms,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "estimated_cost_usd": estimated_cost_usd,
        }
        self.observability.record_event(
            event_type="orchestrator_run",
            source="IADevOrchestratorService",
            duration_ms=total_duration_ms,
            tokens_in=tokens_in or None,
            tokens_out=tokens_out or None,
            cost_usd=estimated_cost_usd or None,
            meta={
                "session_id": sid,
                "intent": classification.get("intent"),
                "domain": domain,
                "output_mode": output_mode,
                "used_tools": used_tools,
            },
        )
        if dictionary_context:
            data_sources["ai_dictionary"]["context"] = {
                "domain": dictionary_context.get("domain"),
                "tables": dictionary_context.get("tables", []),
                "fields": dictionary_context.get("fields", []),
                "rules": dictionary_context.get("rules", []),
                "relations": dictionary_context.get("relations", []),
                "synonyms": dictionary_context.get("synonyms", []),
            }

        return {
            "session_id": sid,
            "reply": reply,
            "orchestrator": {
                "intent": classification.get("intent"),
                "domain": domain,
                "selected_agent": classification.get("selected_agent"),
                "classifier_source": classification.get("classifier_source"),
                "needs_database": needs_database,
                "output_mode": output_mode,
                "used_tools": used_tools,
            },
            "data": payload,
            "actions": actions,
            "data_sources": data_sources,
            "trace": trace,
            "memory": memory_status,
            "observability": observability_payload,
            "active_nodes": self._resolve_active_nodes(
                domain=domain,
                selected_agent=classification.get("selected_agent"),
                used_tools=used_tools,
                has_actions=bool(actions),
                needs_database=needs_database,
            ),
        }

    def run_legacy(
        self,
        message: str,
        session_id: str | None = None,
        reset_memory: bool = False,
    ) -> dict:
        previous = self._is_delegate_skipped()
        self._set_delegate_skipped(True)
        try:
            return self.run(
                message=message,
                session_id=session_id,
                reset_memory=reset_memory,
            )
        finally:
            self._set_delegate_skipped(previous)

    def _is_delegate_skipped(self) -> bool:
        return bool(getattr(self._delegate_state, "skip", False))

    def _set_delegate_skipped(self, value: bool) -> None:
        self._delegate_state.skip = bool(value)

    def reset_memory(self, session_id: str) -> dict:
        sid = (session_id or "").strip()
        if not sid:
            return {"error": "session_id is required"}

        SessionMemoryStore.reset(sid)
        return {
            "session_id": sid,
            "memory": SessionMemoryStore.status(sid),
        }

    def resolve_attendance_period(self, *, message: str, session_id: str | None = None) -> dict:
        text = str(message or "").strip()
        if not text:
            return {"error": "message is required"}

        sid, _ = SessionMemoryStore.get_or_create(session_id)
        session_context = SessionMemoryStore.get_context(sid)
        recent_messages = SessionMemoryStore.get_recent_messages(sid, limit=8)
        rules_period = resolve_period_from_text(text)
        final_period = self._resolve_period_for_attendance(
            text,
            session_context,
            recent_messages,
        )
        period_alternative_hint = self._build_period_alternative_hint(
            message=text,
            period=final_period,
        )

        return {
            "session_id": sid,
            "input": {
                "message": text,
                "explicit_period_detected": self._has_explicit_period(text),
            },
            "resolved_period": self._serialize_period(final_period),
            "rules_fallback_period": self._serialize_period({**rules_period, "source": "rules"}),
            "alternative_hint": period_alternative_hint,
        }

    @staticmethod
    def _serialize_period(period: dict | None) -> dict:
        item = period or {}
        start = item.get("start")
        end = item.get("end")
        payload = {
            "label": str(item.get("label") or ""),
            "source": str(item.get("source") or "rules"),
            "start_date": start.isoformat() if hasattr(start, "isoformat") else None,
            "end_date": end.isoformat() if hasattr(end, "isoformat") else None,
        }
        if "confidence" in item:
            payload["confidence"] = item.get("confidence")
        return payload

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = (text or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    @staticmethod
    def _normalize_identifier(value: object) -> str:
        raw = str(value or "").strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        return digits or raw.lower()

    def _wants_itemized_absence_view(self, message: str) -> bool:
        msg = self._normalize_text(message)
        explicit_tokens = (
            "dia a dia",
            "ausentismo por ausentismo",
            "por ausentismo",
            "fecha por fecha",
            "registro por registro",
            "detalle por dia",
        )
        return any(token in msg for token in explicit_tokens)

    @staticmethod
    def _shape_recurrence_grouped_rows(rows: list[dict]) -> list[dict]:
        grouped_rows: list[dict] = []
        for row in rows:
            grouped_rows.append(
                {
                    "cedula": row.get("cedula", ""),
                    "empleado": row.get("empleado", ""),
                    "supervisor": row.get("supervisor", ""),
                    "cantidad_injustificados": row.get("cantidad_incidencias", 0),
                    "fechas_ausentismo": row.get("fechas", ""),
                }
            )
        return grouped_rows

    def _extract_period_probe_message(self, message: str) -> str | None:
        raw = str(message or "").strip()
        if not raw:
            return None
        normalized = self._normalize_text(raw)
        if not any(
            token in normalized
            for token in ("probar rango", "validar rango", "resolver rango")
        ):
            return None

        cleaned = re.sub(
            r"\b(probar|validar|resolver)\s+rango\b[:\-\s]*",
            "",
            raw,
            flags=re.IGNORECASE,
        ).strip()
        return cleaned or raw

    def _resolve_personal_status_filter(self, *, message: str, session_context: dict | None = None) -> str:
        normalized = self._normalize_text(message)
        if "inactivo" in normalized or "inactivos" in normalized:
            return "inactivos"
        if "activo" in normalized or "activos" in normalized:
            return "activos"

        if _YES_FOLLOW_UP_RE.match(normalized):
            ctx = session_context or {}
            previous = str(ctx.get("last_personal_status") or "").strip().lower()
            if previous in ("all", "activos", "inactivos"):
                return previous

        return "all"

    @staticmethod
    def _format_rows_table(rows: list[dict], max_rows: int = 20) -> str:
        if not rows:
            return "(sin resultados)"

        preview_rows = rows[:max_rows]
        columns = list(preview_rows[0].keys())
        header = " | ".join(columns)
        separator = " | ".join(["---"] * len(columns))
        body = []
        for row in preview_rows:
            body.append(" | ".join(str(row.get(col, "")) for col in columns))

        suffix = ""
        if len(rows) > max_rows:
            suffix = f"\n... ({len(rows) - max_rows} filas adicionales)"

        return f"{header}\n{separator}\n" + "\n".join(body) + suffix

    @staticmethod
    def _format_recent_messages_for_prompt(messages: list[dict], max_messages: int = 6) -> str:
        if not messages:
            return "(sin contexto previo)"

        selected = messages[-max_messages:]
        chunks: list[str] = []
        for item in selected:
            role = str(item.get("role", "unknown"))
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            chunks.append(f"{role}: {content[:300]}")
        return "\n".join(chunks) if chunks else "(sin contexto previo)"

    @staticmethod
    def _has_explicit_period(text: str) -> bool:
        msg = IADevOrchestratorService._normalize_text(text)
        if re.search(r"\d{4}-\d{2}-\d{2}", msg):
            return True
        if re.search(r"\b(lunes|martes|mi.?rcoles|jueves|viernes|s.?bado|domingo)\b", msg):
            return True
        period_tokens = (
            "hoy",
            "ayer",
            "ultima semana",
            "ultimos",
            "mes",
            "anio",
            "rango",
        )
        return any(token in msg for token in period_tokens)

    def _resolve_period_for_attendance(
        self,
        message: str,
        session_context: dict,
        recent_messages: list[dict] | None = None,
    ) -> dict:
        period = resolve_period_from_text(message)
        normalized = self._normalize_text(message)
        explicit_period = self._has_explicit_period(message) or "reincid" in normalized

        if explicit_period:
            openai_period = self._resolve_period_with_openai(
                message=message,
                recent_messages=recent_messages,
                session_context=session_context,
            )
            if openai_period:
                return openai_period
            return {**period, "source": "rules"}

        if not _YES_FOLLOW_UP_RE.match(normalized):
            return {**period, "source": "rules"}

        start = session_context.get("last_period_start")
        end = session_context.get("last_period_end")
        if not start or not end:
            return {**period, "source": "rules"}

        try:
            return {
                "label": "contexto_previo",
                "start": date.fromisoformat(str(start)),
                "end": date.fromisoformat(str(end)),
                "source": "context",
            }
        except ValueError:
            return {**period, "source": "rules"}

    def _resolve_period_with_openai(
        self,
        *,
        message: str,
        recent_messages: list[dict] | None = None,
        session_context: dict | None = None,
    ) -> dict | None:
        if not self.enable_openai_period:
            return None

        openai_api_key = self._get_openai_api_key()
        if not openai_api_key:
            return None

        try:
            from openai import OpenAI

            client = OpenAI(api_key=openai_api_key)
            today_iso = date.today().isoformat()
            history_text = self._format_recent_messages_for_prompt(recent_messages or [])
            context_period = ""
            if session_context:
                start = str(session_context.get("last_period_start") or "").strip()
                end = str(session_context.get("last_period_end") or "").strip()
                if start and end:
                    context_period = f"Last period in session: {start} to {end}"

            response = client.responses.create(
                model=self.period_model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You extract date ranges for attendance analytics.\n"
                            "Return strict JSON: {\"label\":\"...\",\"start_date\":\"YYYY-MM-DD\","
                            "\"end_date\":\"YYYY-MM-DD\",\"confidence\":0.0-1.0}.\n"
                            f"Today is {today_iso}.\n"
                            "Rules:\n"
                            "- If user says 'ultimo mes' and is ambiguous, default to rolling last 30 days.\n"
                            "- If user says 'mes pasado' or 'mes anterior', return previous calendar month.\n"
                            "- Keep end_date <= today."
                        ),
                    },
                    {
                        "role": "system",
                        "content": (
                            "Conversation context (latest first):\n"
                            f"{history_text}\n"
                            f"{context_period}"
                        ),
                    },
                    {"role": "user", "content": message},
                ],
            )
            self._accumulate_openai_usage(self._extract_usage(response))

            text = (getattr(response, "output_text", "") or "").strip()
            if not text:
                return None
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            raw = json_match.group(0) if json_match else text
            data = json.loads(raw)

            start = date.fromisoformat(str(data.get("start_date") or "").strip())
            end = date.fromisoformat(str(data.get("end_date") or "").strip())
            if start > end:
                start, end = end, start
            if end > date.today():
                end = date.today()
            max_window_days = max(30, min(int(os.getenv("IA_DEV_MAX_PERIOD_DAYS", "370")), 1095))
            if (end - start).days > max_window_days:
                return None

            confidence = float(data.get("confidence") or 0.0)
            if confidence < 0.45:
                return None

            return {
                "label": str(data.get("label") or "openai_period"),
                "start": start,
                "end": end,
                "source": "openai_period",
                "confidence": round(confidence, 3),
            }
        except Exception:
            logger.exception("OpenAI period resolution failed")
            return None

    def _build_period_alternative_hint(self, *, message: str, period: dict) -> str | None:
        normalized = self._normalize_text(message)
        label = str(period.get("label") or "").lower()
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

    def _apply_followup_overrides(
        self,
        *,
        message: str,
        classification: dict,
        session_context: dict,
    ) -> dict:
        msg = (message or "").strip()
        normalized = self._normalize_text(msg)
        if not msg:
            return classification

        last_domain = str(session_context.get("last_domain", "") or "").lower()
        last_needs_db = bool(session_context.get("last_needs_database"))
        if (
            _YES_FOLLOW_UP_RE.match(normalized)
            and last_domain == "attendance"
            and last_needs_db
        ):
            merged = dict(classification)
            merged.update(
                {
                    "domain": "attendance",
                    "intent": "attendance_query",
                    "selected_agent": "attendance_agent",
                    "needs_database": True,
                    "output_mode": "table",
                    "needs_personal_join": True,
                    "focus": str(session_context.get("last_focus") or "all"),
                    "classifier_source": f"{classification.get('classifier_source', 'rules')}_followup",
                }
            )
            return merged

        return classification

    def _generate_general_reply(
        self,
        message: str,
        *,
        recent_messages: list[dict] | None = None,
    ) -> str | None:
        if not self.enable_openai_general:
            return None

        openai_api_key = self._get_openai_api_key()
        if not openai_api_key:
            return None

        try:
            from openai import OpenAI

            client = OpenAI(api_key=openai_api_key)
            history_text = self._format_recent_messages_for_prompt(recent_messages or [])
            response = client.responses.create(
                model=self.general_model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "You are an enterprise assistant. Answer clearly and briefly in Spanish. "
                            "If the user asks for general knowledge, answer directly. "
                            "Do not invent internal company data."
                        ),
                    },
                    {
                        "role": "system",
                        "content": (
                            "Conversation context (most recent first, may be empty):\n"
                            f"{history_text}"
                        ),
                    },
                    {"role": "user", "content": message},
                ],
            )
            self._accumulate_openai_usage(self._extract_usage(response))
            text = (getattr(response, "output_text", "") or "").strip()
            return text or None
        except Exception:
            logger.exception("General response generation failed")
            return None

    def _generate_contextual_followup(
        self,
        *,
        message: str,
        base_reply: str,
        domain: str,
        intent: str,
        rowcount: int,
        recent_messages: list[dict] | None = None,
    ) -> str | None:
        if not self.enable_openai_followups:
            return "Si quieres, tambien puedo mostrarlo dia a dia (ausentismo por ausentismo)."

        openai_api_key = self._get_openai_api_key()
        if not openai_api_key:
            return "Si quieres, tambien puedo mostrarlo dia a dia (ausentismo por ausentismo)."

        try:
            from openai import OpenAI

            client = OpenAI(api_key=openai_api_key)
            history_text = self._format_recent_messages_for_prompt(recent_messages or [])
            response = client.responses.create(
                model=self.followup_model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Genera una sugerencia de siguiente paso para chat empresarial.\n"
                            "Responde JSON estricto con llaves: ask_follow_up (boolean), follow_up (string).\n"
                            "Reglas:\n"
                            "- Escribe en espanol latino, maximo 1 pregunta corta.\n"
                            "- Si ya hay una respuesta tabular agregada y puede aportar valor, sugiere ver detalle dia a dia.\n"
                            "- No repitas toda la respuesta previa, no uses markdown.\n"
                            "- Si no hace falta seguimiento, usa ask_follow_up=false y follow_up vacio."
                        ),
                    },
                    {
                        "role": "system",
                        "content": (
                            f"Contexto: domain={domain}, intent={intent}, rowcount={max(0, int(rowcount))}.\n"
                            f"Historial reciente:\n{history_text}\n"
                            f"Respuesta previa:\n{base_reply[:700]}"
                        ),
                    },
                    {"role": "user", "content": message},
                ],
            )
            self._accumulate_openai_usage(self._extract_usage(response))
            text = (getattr(response, "output_text", "") or "").strip()
            if not text:
                return None
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            raw = json_match.group(0) if json_match else text
            data = json.loads(raw)

            ask_follow_up = bool(data.get("ask_follow_up"))
            follow_up = str(data.get("follow_up") or "").strip()
            if not ask_follow_up:
                return None
            if not follow_up:
                return "Si quieres, tambien puedo mostrarlo dia a dia (ausentismo por ausentismo)."
            return follow_up
        except Exception:
            logger.exception("Contextual follow-up generation failed")
            return "Si quieres, tambien puedo mostrarlo dia a dia (ausentismo por ausentismo)."

    def _accumulate_openai_usage(self, usage: dict | None):
        current = self._last_openai_usage or {"tokens_in": 0, "tokens_out": 0}
        incoming = usage or {}
        current["tokens_in"] = int(current.get("tokens_in") or 0) + int(incoming.get("tokens_in") or 0)
        current["tokens_out"] = int(current.get("tokens_out") or 0) + int(incoming.get("tokens_out") or 0)
        self._last_openai_usage = current

    @staticmethod
    def _extract_usage(response) -> dict:
        usage = getattr(response, "usage", None)
        if usage is None:
            return {"tokens_in": 0, "tokens_out": 0}
        try:
            input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
            return {
                "tokens_in": input_tokens,
                "tokens_out": output_tokens,
            }
        except Exception:
            return {"tokens_in": 0, "tokens_out": 0}

    @staticmethod
    def _estimate_openai_cost(*, model: str, tokens_in: int, tokens_out: int) -> float:
        in_k = max(0, int(tokens_in)) / 1000.0
        out_k = max(0, int(tokens_out)) / 1000.0
        # Default conservador para modelos mini/nano; ajustar por entorno si cambia el pricing.
        try:
            in_price = float(os.getenv("IA_DEV_OPENAI_INPUT_PRICE_PER_1K", "0.0002"))
        except Exception:
            in_price = 0.0002
        try:
            out_price = float(os.getenv("IA_DEV_OPENAI_OUTPUT_PRICE_PER_1K", "0.0008"))
        except Exception:
            out_price = 0.0008
        model_name = (model or "").strip().lower()
        if "gpt-5" in model_name and "nano" in model_name:
            try:
                in_price = float(os.getenv("IA_DEV_OPENAI_INPUT_PRICE_PER_1K", "0.00005"))
            except Exception:
                in_price = 0.00005
            try:
                out_price = float(os.getenv("IA_DEV_OPENAI_OUTPUT_PRICE_PER_1K", "0.0002"))
            except Exception:
                out_price = 0.0002
        return round((in_k * in_price) + (out_k * out_price), 8)

    @staticmethod
    def _resolve_active_nodes(
        domain: str,
        selected_agent: str | None,
        used_tools: list[str],
        has_actions: bool,
        needs_database: bool = False,
    ) -> list[str]:
        active = {"q", "gpt", "route"}
        domain_key = (domain or "").strip().lower()
        agent_key = (selected_agent or "").strip().lower()

        if needs_database:
            active.add("meta")
        else:
            active.add("result")

        if domain_key in ("attendance", "rrhh") and needs_database:
            active.update(
                {
                    "aus",
                    "personal",
                    "join",
                    "rules",
                    "check",
                    "audit",
                    "result",
                }
            )
        elif domain_key == "transport":
            active.update({"transport"})
            if needs_database and has_actions:
                active.update({"alert", "audit"})
            elif needs_database:
                active.update({"join", "rules", "check", "audit", "result"})
            else:
                active.add("result")
        elif domain_key == "operations" and needs_database:
            active.update({"operacion", "join", "rules", "check", "audit", "result"})
        elif domain_key in ("payroll", "audit", "viatics"):
            active.update({"audit", "result"})

        if "rrhh_agent" == agent_key:
            active.add("personal")
        if "attendance_agent" == agent_key:
            active.add("aus")

        if "get_attendance_summary" in used_tools:
            active.update({"aus", "join", "rules", "check", "audit", "result"})
        if "get_attendance_recurrent_unjustified_with_supervisor" in used_tools:
            active.update(
                {
                    "aus",
                    "personal",
                    "join",
                    "rules",
                    "check",
                    "audit",
                    "result",
                }
            )
        if "get_attendance_unjustified_with_personal" in used_tools:
            active.update(
                {
                    "aus",
                    "personal",
                    "join",
                    "rules",
                    "check",
                    "audit",
                    "result",
                }
            )
        if "get_attendance_unjustified_table" in used_tools:
            active.update({"aus", "join", "rules", "check", "audit", "result"})
        if "get_attendance_detail_with_personal" in used_tools:
            active.update(
                {
                    "aus",
                    "personal",
                    "join",
                    "rules",
                    "check",
                    "audit",
                    "result",
                }
            )
        if "get_transport_departures_summary" in used_tools:
            active.update(
                {
                    "transport",
                    "join",
                    "rules",
                    "check",
                    "audit",
                    "result",
                }
            )

        if has_actions:
            active.update({"alert", "audit"})

        return sorted(active)






