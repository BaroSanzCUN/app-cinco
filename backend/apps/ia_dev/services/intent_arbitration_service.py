from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from apps.ia_dev.application.contracts.query_intelligence_contracts import StructuredQueryIntent
from apps.ia_dev.application.taxonomia_dominios import normalizar_codigo_dominio
from apps.ia_dev.infrastructure.ai.model_routing import resolve_model_name


logger = logging.getLogger(__name__)


class IntentArbitrationService:
    SUPPORTED_INTENTS = {
        "analytics_query",
        "knowledge_change_request",
        "operational_question",
        "action_request",
        "fallback",
    }
    ANALYTICS_DOMAINS = {"ausentismo", "attendance", "empleados", "rrhh"}

    def __init__(self):
        self.enable_openai = str(
            os.getenv("IA_DEV_USE_OPENAI_INTENT_ARBITRATION", "1") or ""
        ).strip().lower() in {"1", "true", "yes", "on"}
        self.model = resolve_model_name("intent_arbitration")
        self.confidence_threshold = self._read_threshold(
            "IA_DEV_INTENT_ARBITRATION_CONFIDENCE_THRESHOLD",
            default=0.68,
        )
        self.clarification_threshold = self._read_threshold(
            "IA_DEV_INTENT_ARBITRATION_CLARIFICATION_THRESHOLD",
            default=0.55,
        )

    @staticmethod
    def _read_threshold(name: str, *, default: float) -> float:
        raw = str(os.getenv(name, str(default)) or str(default)).strip()
        try:
            value = float(raw)
        except ValueError:
            value = default
        return max(0.0, min(value, 1.0))

    @staticmethod
    def _get_openai_api_key() -> str:
        return str(
            os.getenv("OPENAI_API_KEY") or os.getenv("IA_DEV_OPENAI_API_KEY") or ""
        ).strip()

    def arbitrate(
        self,
        *,
        original_question: str,
        candidate_domain: str,
        heuristic_intent: dict[str, Any] | str | None,
        llm_intent: StructuredQueryIntent | dict[str, Any] | str | None,
        candidate_capabilities: list[dict[str, Any]] | None,
        ai_dictionary_context: dict[str, Any] | None,
        action_risk: dict[str, Any] | None,
        knowledge_governance_signals: dict[str, Any] | None,
    ) -> dict[str, Any]:
        heuristic_payload = self._compact_heuristic_intent(heuristic_intent=heuristic_intent)
        llm_payload = self._compact_llm_intent(llm_intent=llm_intent)
        capabilities_payload = self._compact_capabilities(candidate_capabilities)
        dictionary_payload = self._compact_dictionary_context(ai_dictionary_context)
        action_payload = dict(action_risk or {})
        governance_payload = dict(knowledge_governance_signals or {})
        fallback = self._build_deterministic_fallback(
            original_question=original_question,
            candidate_domain=candidate_domain,
            heuristic_payload=heuristic_payload,
            llm_payload=llm_payload,
            capabilities_payload=capabilities_payload,
            dictionary_payload=dictionary_payload,
            action_payload=action_payload,
            governance_payload=governance_payload,
        )

        decision = dict(fallback)
        source = "deterministic_fallback"
        if self.enable_openai and self._get_openai_api_key():
            try:
                llm_decision = self._arbitrate_openai(
                    original_question=original_question,
                    candidate_domain=candidate_domain,
                    heuristic_payload=heuristic_payload,
                    llm_payload=llm_payload,
                    capabilities_payload=capabilities_payload,
                    dictionary_payload=dictionary_payload,
                    action_payload=action_payload,
                    governance_payload=governance_payload,
                )
                decision.update(
                    {
                        key: value
                        for key, value in llm_decision.items()
                        if value not in (None, "")
                    }
                )
                source = "openai"
            except Exception:
                logger.exception("Intent arbitration fallback to deterministic policy")
                source = "openai_error_fallback"

        final = self._apply_minimal_policy(
            decision=decision,
            fallback=fallback,
            capabilities_payload=capabilities_payload,
            dictionary_payload=dictionary_payload,
            action_payload=action_payload,
            governance_payload=governance_payload,
        )
        final["source"] = source
        final["heuristic_intent"] = heuristic_payload.get("intent")
        final["llm_intent"] = llm_payload.get("intent")
        return final

    def _arbitrate_openai(
        self,
        *,
        original_question: str,
        candidate_domain: str,
        heuristic_payload: dict[str, Any],
        llm_payload: dict[str, Any],
        capabilities_payload: list[dict[str, Any]],
        dictionary_payload: dict[str, Any],
        action_payload: dict[str, Any],
        governance_payload: dict[str, Any],
    ) -> dict[str, Any]:
        from openai import OpenAI

        client = OpenAI(api_key=self._get_openai_api_key())
        response = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Eres la capa de arbitraje de intencion para un runtime empresarial.\n"
                        "Debes decidir semanticamente si la solicitud es una consulta analitica, "
                        "un cambio de conocimiento, una pregunta operativa, una accion o un fallback.\n"
                        "Devuelve SOLO JSON con estas llaves: final_intent, final_domain, should_execute_query, "
                        "should_create_kpro, should_use_sql_assisted, should_use_handler, should_fallback, "
                        "confidence, reasoning_summary, required_clarification.\n"
                        "final_intent permitido: analytics_query, knowledge_change_request, "
                        "operational_question, action_request, fallback.\n"
                        "Regla critica: solo activa should_create_kpro=true si el usuario pide explicitamente "
                        "crear conocimiento, modificar reglas, registrar una definicion, cambiar metadata "
                        "o aprobar/aplicar una propuesta. Una pregunta analitica nunca crea KPRO por defecto.\n"
                        "Si la confianza es baja, usa final_intent=fallback y required_clarification."
                    ),
                },
                {
                    "role": "system",
                    "content": (
                        "Ejemplos contrastivos:\n"
                        '- "Que patrones existen por area, cargo y sede" => '
                        '{"final_intent":"analytics_query","final_domain":"ausentismo","should_create_kpro":false,"should_use_sql_assisted":true}\n'
                        '- "Agrega una nueva regla para interpretar sede como zona_nodo" => '
                        '{"final_intent":"knowledge_change_request","should_create_kpro":true}\n'
                        '- "Modifica el diccionario para que incapacidad sea sinonimo de ausencia medica" => '
                        '{"final_intent":"knowledge_change_request","should_create_kpro":true}\n'
                        '- "Que cargos concentran mas incapacidades" => '
                        '{"final_intent":"analytics_query","should_create_kpro":false}\n'
                    ),
                },
                {
                    "role": "system",
                    "content": json.dumps(
                        {
                            "original_question": original_question,
                            "candidate_domain": candidate_domain,
                            "heuristic_intent": heuristic_payload,
                            "llm_intent": llm_payload,
                            "candidate_capabilities": capabilities_payload,
                            "ai_dictionary_context": dictionary_payload,
                            "action_risk": action_payload,
                            "knowledge_governance_signals": governance_payload,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        raw_text = str(getattr(response, "output_text", "") or "").strip()
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        return self._safe_json(match.group(0) if match else raw_text)

    def _build_deterministic_fallback(
        self,
        *,
        original_question: str,
        candidate_domain: str,
        heuristic_payload: dict[str, Any],
        llm_payload: dict[str, Any],
        capabilities_payload: list[dict[str, Any]],
        dictionary_payload: dict[str, Any],
        action_payload: dict[str, Any],
        governance_payload: dict[str, Any],
    ) -> dict[str, Any]:
        normalized_domain = normalizar_codigo_dominio(
            llm_payload.get("domain")
            or candidate_domain
            or heuristic_payload.get("domain")
            or "general"
        )
        final_intent = "fallback"
        confidence = max(
            float(llm_payload.get("confidence") or 0.0),
            float(heuristic_payload.get("confidence") or 0.0),
            0.42,
        )
        explicit_kpro = bool(governance_payload.get("explicit_change_request"))
        explicit_apply = bool(governance_payload.get("explicit_apply_request"))
        llm_intent = str(llm_payload.get("intent") or "").strip().lower()
        heuristic_intent = str(heuristic_payload.get("intent") or "").strip().lower()
        llm_operation = str(llm_payload.get("operation") or "").strip().lower()

        if explicit_kpro or explicit_apply or llm_intent == "knowledge_change_request":
            final_intent = "knowledge_change_request"
            normalized_domain = "knowledge"
            confidence = max(confidence, 0.78)
        elif self._looks_like_analytics(
            domain_code=normalized_domain,
            llm_intent=llm_intent,
            llm_operation=llm_operation,
            heuristic_intent=heuristic_intent,
            capabilities_payload=capabilities_payload,
        ):
            final_intent = "analytics_query"
            confidence = max(confidence, 0.72)
        elif heuristic_intent in {"create_ticket", "action_request"}:
            final_intent = "action_request"
            confidence = max(confidence, 0.7)
        elif normalized_domain in {"operations", "transport", "transporte"}:
            final_intent = "operational_question"
            confidence = max(confidence, 0.64)

        clarification = ""
        if final_intent == "fallback" or confidence < self.clarification_threshold:
            clarification = (
                "Aclara si quieres consultar datos existentes, cambiar conocimiento o ejecutar una accion."
            )

        return {
            "final_intent": final_intent,
            "final_domain": normalized_domain or "general",
            "should_execute_query": final_intent == "analytics_query",
            "should_create_kpro": final_intent == "knowledge_change_request" and (explicit_kpro or explicit_apply),
            "should_use_sql_assisted": (
                final_intent == "analytics_query"
                and bool(dictionary_payload.get("has_real_data"))
                and normalized_domain in {"ausentismo", "attendance"}
            ),
            "should_use_handler": (
                final_intent == "analytics_query"
                and any(item.get("capability_id") for item in capabilities_payload)
            ),
            "should_fallback": bool(clarification) or final_intent == "fallback",
            "confidence": confidence,
            "reasoning_summary": self._default_reasoning_summary(
                final_intent=final_intent,
                normalized_domain=normalized_domain,
                has_real_data=bool(dictionary_payload.get("has_real_data")),
                original_question=original_question,
                action_payload=action_payload,
            ),
            "required_clarification": clarification,
        }

    def _apply_minimal_policy(
        self,
        *,
        decision: dict[str, Any],
        fallback: dict[str, Any],
        capabilities_payload: list[dict[str, Any]],
        dictionary_payload: dict[str, Any],
        action_payload: dict[str, Any],
        governance_payload: dict[str, Any],
    ) -> dict[str, Any]:
        final_intent = str(decision.get("final_intent") or fallback.get("final_intent") or "fallback").strip().lower()
        if final_intent not in self.SUPPORTED_INTENTS:
            final_intent = "fallback"
        final_domain = normalizar_codigo_dominio(
            decision.get("final_domain") or fallback.get("final_domain") or "general"
        ) or "general"
        confidence = float(decision.get("confidence") or fallback.get("confidence") or 0.0)
        reasoning_summary = str(
            decision.get("reasoning_summary")
            or fallback.get("reasoning_summary")
            or "Arbitraje semantico sin detalle adicional."
        ).strip()
        clarification = str(
            decision.get("required_clarification")
            or fallback.get("required_clarification")
            or ""
        ).strip()
        explicit_kpro = bool(governance_payload.get("explicit_change_request"))
        explicit_apply = bool(governance_payload.get("explicit_apply_request"))
        has_real_data = bool(dictionary_payload.get("has_real_data"))
        low_confidence = confidence < self.confidence_threshold

        should_execute_query = bool(decision.get("should_execute_query"))
        should_create_kpro = bool(decision.get("should_create_kpro"))
        should_use_sql_assisted = bool(decision.get("should_use_sql_assisted"))
        should_use_handler = bool(decision.get("should_use_handler"))
        should_fallback = bool(decision.get("should_fallback"))

        if final_intent == "analytics_query":
            should_create_kpro = False
            should_execute_query = not low_confidence and final_domain not in {"", "general", "knowledge"}
            should_use_sql_assisted = (
                should_execute_query
                and has_real_data
                and final_domain in {"ausentismo", "attendance"}
            )
            should_use_handler = (
                should_execute_query
                and not should_use_sql_assisted
                and any(item.get("capability_id") for item in capabilities_payload)
            )

        elif final_intent == "knowledge_change_request":
            should_execute_query = False
            should_use_sql_assisted = False
            should_use_handler = False
            should_create_kpro = bool(explicit_kpro or explicit_apply)
            final_domain = "knowledge"

        elif final_intent in {"operational_question", "action_request"}:
            should_execute_query = False
            should_create_kpro = False
            should_use_sql_assisted = False
            should_use_handler = final_intent == "action_request" and any(
                item.get("capability_id") for item in capabilities_payload
            )

        else:
            should_execute_query = False
            should_create_kpro = False
            should_use_sql_assisted = False
            should_use_handler = False

        if low_confidence:
            should_fallback = True
            should_execute_query = False
            should_use_sql_assisted = False
            if not clarification:
                clarification = (
                    "Aclara si buscas analitica de datos, un cambio de conocimiento o una accion operativa."
                )

        if not has_real_data and final_intent == "analytics_query":
            should_use_sql_assisted = False

        return {
            "final_intent": final_intent,
            "final_domain": final_domain,
            "should_execute_query": bool(should_execute_query),
            "should_create_kpro": bool(should_create_kpro),
            "should_use_sql_assisted": bool(should_use_sql_assisted),
            "should_use_handler": bool(should_use_handler),
            "should_fallback": bool(should_fallback or low_confidence),
            "confidence": confidence,
            "reasoning_summary": reasoning_summary[:280],
            "required_clarification": clarification[:280],
            "policy": {
                "low_confidence": low_confidence,
                "confidence_threshold": self.confidence_threshold,
                "clarification_threshold": self.clarification_threshold,
                "has_real_data": has_real_data,
                "free_sql_allowed": False,
            },
            "kpro_blocked_by_arbitration": bool(
                final_intent == "analytics_query" and not should_create_kpro
            ),
            "sql_assisted_selected_by_arbitration": bool(should_use_sql_assisted),
        }

    @classmethod
    def _looks_like_analytics(
        cls,
        *,
        domain_code: str,
        llm_intent: str,
        llm_operation: str,
        heuristic_intent: str,
        capabilities_payload: list[dict[str, Any]],
    ) -> bool:
        if llm_intent == "knowledge_change_request":
            return False
        if domain_code in cls.ANALYTICS_DOMAINS and llm_operation in {
            "aggregate",
            "count",
            "compare",
            "trend",
            "detail",
            "summary",
        }:
            return True
        if heuristic_intent in {"ausentismo_query", "empleados_query"}:
            return True
        return any(
            str(item.get("capability_id") or "").startswith(("attendance.", "empleados."))
            for item in capabilities_payload
        )

    @staticmethod
    def _compact_heuristic_intent(heuristic_intent: dict[str, Any] | str | None) -> dict[str, Any]:
        if isinstance(heuristic_intent, dict):
            return {
                "intent": str(heuristic_intent.get("intent") or "").strip().lower(),
                "domain": normalizar_codigo_dominio(heuristic_intent.get("domain") or ""),
                "confidence": float(heuristic_intent.get("confidence") or 0.0),
                "needs_database": bool(heuristic_intent.get("needs_database")),
                "selected_agent": str(heuristic_intent.get("selected_agent") or "").strip(),
            }
        return {
            "intent": str(heuristic_intent or "").strip().lower(),
            "domain": "",
            "confidence": 0.0,
            "needs_database": False,
            "selected_agent": "",
        }

    @staticmethod
    def _compact_llm_intent(
        llm_intent: StructuredQueryIntent | dict[str, Any] | str | None,
    ) -> dict[str, Any]:
        if isinstance(llm_intent, StructuredQueryIntent):
            return {
                "intent": str(llm_intent.operation or "").strip().lower(),
                "domain": normalizar_codigo_dominio(llm_intent.domain_code),
                "operation": str(llm_intent.operation or "").strip().lower(),
                "template_id": str(llm_intent.template_id or "").strip().lower(),
                "confidence": float(llm_intent.confidence or 0.0),
                "source": str(llm_intent.source or "").strip().lower(),
                "group_by": list(llm_intent.group_by or []),
                "metrics": list(llm_intent.metrics or []),
            }
        if isinstance(llm_intent, dict):
            return {
                "intent": str(llm_intent.get("operation") or llm_intent.get("intent") or "").strip().lower(),
                "domain": normalizar_codigo_dominio(llm_intent.get("domain_code") or llm_intent.get("domain") or ""),
                "operation": str(llm_intent.get("operation") or "").strip().lower(),
                "template_id": str(llm_intent.get("template_id") or "").strip().lower(),
                "confidence": float(llm_intent.get("confidence") or 0.0),
                "source": str(llm_intent.get("source") or "").strip().lower(),
                "group_by": list(llm_intent.get("group_by") or []),
                "metrics": list(llm_intent.get("metrics") or []),
            }
        return {
            "intent": str(llm_intent or "").strip().lower(),
            "domain": "",
            "operation": "",
            "template_id": "",
            "confidence": 0.0,
            "source": "",
            "group_by": [],
            "metrics": [],
        }

    @staticmethod
    def _compact_capabilities(candidate_capabilities: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in list(candidate_capabilities or []):
            if not isinstance(item, dict):
                continue
            capability_id = str(item.get("capability_id") or "").strip()
            if not capability_id:
                continue
            result.append(
                {
                    "capability_id": capability_id,
                    "reason": str(item.get("reason") or "").strip(),
                    "source_domain": normalizar_codigo_dominio(item.get("source_domain") or ""),
                }
            )
        return result[:6]

    @staticmethod
    def _compact_dictionary_context(ai_dictionary_context: dict[str, Any] | None) -> dict[str, Any]:
        context = dict(ai_dictionary_context or {})
        fields = list(context.get("fields") or [])
        relations = list(context.get("relations") or [])
        rules = list(context.get("rules") or [])
        return {
            "fields_count": len(fields),
            "relations_count": len(relations),
            "rules_count": len(rules),
            "has_real_data": bool(fields or relations),
        }

    @staticmethod
    def _default_reasoning_summary(
        *,
        final_intent: str,
        normalized_domain: str,
        has_real_data: bool,
        original_question: str,
        action_payload: dict[str, Any],
    ) -> str:
        if final_intent == "analytics_query":
            source = "con ai_dictionary" if has_real_data else "sin soporte estructural suficiente"
            return f"Consulta analitica sobre {normalized_domain or 'datos existentes'} {source}; no implica cambio de conocimiento."
        if final_intent == "knowledge_change_request":
            return "La solicitud pide cambiar conocimiento gobernado y requiere proposal/KPRO antes de aplicar cambios."
        if final_intent == "action_request":
            return "La solicitud apunta a ejecutar una accion y no a consultar datos historicos."
        if final_intent == "operational_question":
            return "La solicitud es operativa y no corresponde a analytics gobernado por SQL assisted."
        risk_level = str(action_payload.get("level") or "low").strip().lower()
        return (
            f"No hay suficiente certeza para arbitrar la intencion final (risk={risk_level}); "
            f"se requiere aclaracion sobre: {original_question[:120]}"
        )

    @staticmethod
    def _safe_json(raw: str) -> dict[str, Any]:
        try:
            data = json.loads(str(raw or "{}"))
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
