import logging
import os
import re
import unicodedata
from datetime import date, datetime

from .dictionary_tool_service import DictionaryToolService
from .intent_service import IntentClassifierService
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
        self.transport_tool = TransportToolService()
        self.enable_openai_general = os.getenv(
            "IA_DEV_USE_OPENAI_GENERAL", "1"
        ).strip().lower() in ("1", "true", "yes", "on")
        self.general_model = os.getenv(
            "IA_DEV_GENERAL_MODEL", os.getenv("IA_DEV_MODEL", "gpt-5-nano")
        )

    @staticmethod
    def _get_openai_api_key() -> str:
        return (
            os.getenv("OPENAI_API_KEY") or os.getenv("IA_DEV_OPENAI_API_KEY") or ""
        ).strip()

    def run(self, message: str, session_id: str | None = None, reset_memory: bool = False) -> dict:
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
                dictionary_status = self.dictionary_tool.check_connection()
                data_sources["ai_dictionary"] = dictionary_status
                used_tools.append("check_ai_dictionary_connection")
                push_trace(
                    "data_source_check",
                    "ok",
                    {"ai_dictionary": dictionary_status},
                    {"q", "gpt", "route", "meta"},
                )
                try:
                    dictionary_snapshot = self.dictionary_tool.get_dictionary_snapshot()
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
                    dictionary_context = self.dictionary_tool.get_domain_context(domain)
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
                transport_status = self.transport_tool.source_status()
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

        if domain == "attendance" and needs_database:
            period = self._resolve_period_for_attendance(message, session_context)
            push_trace(
                "period_resolver",
                "ok",
                period,
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
                        recurrence = self.attendance_tool.get_recurrent_unjustified_with_supervisor(
                            period["start"],
                            period["end"],
                            threshold=2,
                            limit=150,
                        )
                        used_tools.append("get_attendance_recurrent_unjustified_with_supervisor")
                        rows = recurrence.get("rows", [])
                        payload["table"] = {
                            "columns": list(rows[0].keys()) if rows else [],
                            "rows": rows,
                            "rowcount": int(recurrence.get("rowcount") or len(rows)),
                        }
                        payload["kpis"] = {
                            "total_reincidentes": int(recurrence.get("rowcount") or 0),
                            "umbral_reincidencia": int(recurrence.get("threshold") or 2),
                        }
                        if not rows:
                            reply = (
                                f"No se encontraron reincidentes injustificados entre "
                                f"{recurrence['periodo_inicio']} y {recurrence['periodo_fin']}."
                            )
                        else:
                            preview = self._format_rows_table(rows)
                            reply = (
                                f"Reincidentes injustificados en la ventana {recurrence['periodo_inicio']} "
                                f"a {recurrence['periodo_fin']} (umbral >= {recurrence['threshold']}), "
                                f"total={payload['kpis']['total_reincidentes']}:\n\n{preview}"
                            )
                    elif focus == "unjustified":
                        if needs_personal_join:
                            try:
                                detail = self.attendance_tool.get_unjustified_with_personal(
                                    period["start"], period["end"], limit=150
                                )
                                used_tools.append("get_attendance_unjustified_with_personal")
                            except Exception as join_exc:
                                detail = self.attendance_tool.get_unjustified_table(
                                    period["start"], period["end"], limit=150
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
                            detail = self.attendance_tool.get_unjustified_table(
                                period["start"], period["end"], limit=150
                            )
                            used_tools.append("get_attendance_unjustified_table")

                        rows = detail.get("rows", [])
                        payload["table"] = {
                            "columns": list(rows[0].keys()) if rows else [],
                            "rows": rows,
                            "rowcount": int(detail.get("rowcount") or len(rows)),
                        }

                        if not rows:
                            reply = (
                                f"No se encontraron ausentismos injustificados entre "
                                f"{detail['periodo_inicio']} y {detail['periodo_fin']}."
                            )
                        else:
                            preview = self._format_rows_table(rows)
                            reply = (
                                f"Tabla de ausentismos injustificados del periodo "
                                f"{detail['periodo_inicio']} al {detail['periodo_fin']} "
                                f"({payload['table']['rowcount']} filas):\n\n{preview}"
                            )
                    else:
                        detail = self.attendance_tool.get_detail_with_personal(
                            period["start"], period["end"], limit=150
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
                    summary = self.attendance_tool.get_summary(period["start"], period["end"])
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
                    summary = self.transport_tool.get_departures_summary(period["end"])
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
            llm_reply = self._generate_general_reply(
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
            "active_nodes": self._resolve_active_nodes(
                domain=domain,
                selected_agent=classification.get("selected_agent"),
                used_tools=used_tools,
                has_actions=bool(actions),
                needs_database=needs_database,
            ),
        }

    def reset_memory(self, session_id: str) -> dict:
        sid = (session_id or "").strip()
        if not sid:
            return {"error": "session_id is required"}

        SessionMemoryStore.reset(sid)
        return {
            "session_id": sid,
            "memory": SessionMemoryStore.status(sid),
        }

    @staticmethod
    def _normalize_text(text: str) -> str:
        lowered = (text or "").strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

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

    def _resolve_period_for_attendance(self, message: str, session_context: dict) -> dict:
        period = resolve_period_from_text(message)
        if self._has_explicit_period(message):
            return period

        if not _YES_FOLLOW_UP_RE.match(self._normalize_text(message)):
            return period

        start = session_context.get("last_period_start")
        end = session_context.get("last_period_end")
        if not start or not end:
            return period

        try:
            return {
                "label": "contexto_previo",
                "start": date.fromisoformat(str(start)),
                "end": date.fromisoformat(str(end)),
            }
        except ValueError:
            return period

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
            text = (getattr(response, "output_text", "") or "").strip()
            return text or None
        except Exception:
            logger.exception("General response generation failed")
            return None

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

