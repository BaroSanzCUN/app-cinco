import hmac
import os
import re
import time
import uuid

from django.db import connections, transaction

from .sql_store import IADevSqlStore


_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
_RULE_CODE_RE = re.compile(r"^RN-(\d+)$", re.IGNORECASE)
_PROPOSAL_TYPES = {"nueva_regla", "actualizacion_regla"}


class KnowledgeGovernanceService:
    def __init__(self):
        self.db_alias = os.getenv("IA_DEV_DB_ALIAS", "default").strip() or "default"
        dictionary_table = os.getenv(
            "IA_DEV_DICTIONARY_TABLE",
            "ai_dictionary.dd_dominios",
        ).strip()
        self.schema = dictionary_table.split(".", 1)[0] if "." in dictionary_table else "ai_dictionary"
        self.mode = self._normalize_mode(
            os.getenv("IA_DEV_KNOWLEDGE_GOVERNANCE_MODE", "ceo")
        )
        self.ceo_auth_key = os.getenv("IA_DEV_CEO_AUTH_KEY", "").strip()
        self.store = IADevSqlStore()

    @staticmethod
    def _normalize_mode(raw: str) -> str:
        value = (raw or "ceo").strip().lower()
        if value in ("ceo", "auto", "directo"):
            return value
        return "ceo"

    @staticmethod
    def _now() -> int:
        return int(time.time())

    def _safe_schema(self) -> str:
        if not _SAFE_IDENTIFIER_RE.match(self.schema):
            raise ValueError("Invalid ai_dictionary schema")
        return self.schema

    def validate_auth_key(self, auth_key: str | None) -> bool:
        if self.mode != "ceo":
            return True
        if not self.ceo_auth_key:
            return False
        provided = (auth_key or "").strip()
        return hmac.compare_digest(provided, self.ceo_auth_key)

    def _fetchall(self, sql: str, params: list | tuple | None = None) -> list[tuple]:
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params or [])
            return cursor.fetchall()

    def _fetchone(self, sql: str, params: list | tuple | None = None) -> tuple | None:
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params or [])
            return cursor.fetchone()

    def _get_rule_columns(self) -> set[str]:
        schema = self._safe_schema()
        rows = self._fetchall(
            """
            SELECT COLUMN_NAME
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = 'dd_reglas'
            """,
            [schema],
        )
        return {str(row[0]) for row in rows if row and row[0]}

    def _resolve_domain_id(self, domain_code: str) -> int:
        schema = self._safe_schema()
        code = (domain_code or "GENERAL").strip().upper()
        row = self._fetchone(
            f"""
            SELECT id
            FROM {schema}.dd_dominios
            WHERE activo = 1
              AND UPPER(codigo) = %s
            LIMIT 1
            """,
            [code],
        )
        if row:
            return int(row[0])

        fallback = self._fetchone(
            f"""
            SELECT id
            FROM {schema}.dd_dominios
            WHERE activo = 1
            ORDER BY id
            LIMIT 1
            """
        )
        if not fallback:
            raise ValueError("No hay dominios activos en ai_dictionary.dd_dominios")
        return int(fallback[0])

    def _next_rule_code(self) -> str:
        schema = self._safe_schema()
        rows = self._fetchall(
            f"""
            SELECT codigo
            FROM {schema}.dd_reglas
            WHERE codigo LIKE 'RN-%'
            ORDER BY id DESC
            LIMIT 200
            """
        )
        max_value = 0
        for row in rows:
            if not row:
                continue
            match = _RULE_CODE_RE.match(str(row[0] or "").strip())
            if not match:
                continue
            max_value = max(max_value, int(match.group(1)))
        return f"RN-{max_value + 1:03d}"

    def find_similar_rules(self, text: str, *, limit: int = 10) -> list[dict]:
        schema = self._safe_schema()
        term = (text or "").strip()
        if not term:
            return []
        safe_limit = max(1, min(int(limit), 20))
        pattern = f"%{term}%"
        rows = self._fetchall(
            f"""
            SELECT
                r.id,
                r.codigo,
                r.nombre,
                d.codigo AS dominio_codigo,
                r.resultado_funcional,
                r.prioridad
            FROM {schema}.dd_reglas AS r
            JOIN {schema}.dd_dominios AS d ON d.id = r.dominio_id
            WHERE r.activo = 1
              AND (
                    r.nombre LIKE %s
                    OR r.condicion_sql LIKE %s
                    OR r.resultado_funcional LIKE %s
              )
            ORDER BY r.prioridad, r.codigo
            LIMIT %s
            """,
            [pattern, pattern, pattern, safe_limit],
        )
        return [
            {
                "id": int(row[0]),
                "codigo": str(row[1] or ""),
                "nombre": str(row[2] or ""),
                "dominio_codigo": str(row[3] or ""),
                "resultado_funcional": str(row[4] or ""),
                "prioridad": int(row[5] or 0),
            }
            for row in rows
        ]

    @staticmethod
    def _guess_domain_code(message: str) -> str:
        text = (message or "").strip().lower()
        if any(token in text for token in ("ausent", "asistencia", "injustific", "justific")):
            return "AUSENTISMOS"
        if any(token in text for token in ("rrhh", "emplead", "supervisor", "cargo", "area", "carpeta")):
            return "USUARIOS"
        if any(token in text for token in ("transporte", "vehicul", "ruta", "salida")):
            return "TRANSPORTE"
        if any(token in text for token in ("nomina", "pago", "devengo", "descuento")):
            return "NOMINA"
        if any(token in text for token in ("viatic", "reembolso", "gasto")):
            return "VIATICOS"
        if any(token in text for token in ("operacion", "actividad", "ot")):
            return "OPERACIONES"
        if any(token in text for token in ("auditor", "traza", "control")):
            return "AUDITORIA"
        return "GENERAL"

    @staticmethod
    def _guess_tables(domain_code: str) -> str:
        mapping = {
            "AUSENTISMOS": "cincosas_cincosas.gestionh_ausentismo,cincosas_cincosas.cinco_base_de_personal",
            "USUARIOS": "cincosas_cincosas.cinco_base_de_personal",
            "TRANSPORTE": "pendiente_configurar_fuente_transporte",
            "NOMINA": "pendiente_mapeo_nomina",
            "VIATICOS": "pendiente_mapeo_viaticos",
            "OPERACIONES": "pendiente_mapeo_operaciones",
            "AUDITORIA": "pendiente_mapeo_auditoria",
            "GENERAL": "",
        }
        return mapping.get((domain_code or "").strip().upper(), "")

    @staticmethod
    def _extract_target_rule_id(message: str) -> int | None:
        msg = (message or "").strip().lower()
        match = re.search(r"\b(?:id|regla)\s*#?\s*(\d+)\b", msg)
        if not match:
            return None
        return int(match.group(1))

    def create_proposal_from_message(
        self,
        *,
        message: str,
        session_id: str | None = None,
        requested_by: str = "analista_agent",
    ) -> dict:
        clean_message = (message or "").strip()
        if not clean_message:
            return {"ok": False, "error": "message is required"}

        lowered = clean_message.lower()
        proposal_type = "actualizacion_regla" if "actualizar regla" in lowered or "modificar regla" in lowered else "nueva_regla"
        domain_code = self._guess_domain_code(clean_message)
        target_rule_id = self._extract_target_rule_id(clean_message) if proposal_type == "actualizacion_regla" else None
        name = (
            "Actualizacion de regla propuesta desde IA DEV"
            if proposal_type == "actualizacion_regla"
            else "Nueva regla propuesta desde IA DEV"
        )

        return self.create_proposal(
            proposal_type=proposal_type,
            name=name,
            description=clean_message,
            domain_code=domain_code,
            condition_sql="",
            result_text=(
                "Regla propuesta por IA DEV. Ajusta condicion SQL y resultado funcional "
                "antes de promoverla a productivo."
            ),
            tables_related=self._guess_tables(domain_code),
            priority=50,
            target_rule_id=target_rule_id,
            session_id=session_id,
            requested_by=requested_by,
        )

    def create_proposal(
        self,
        *,
        proposal_type: str,
        name: str,
        description: str,
        domain_code: str = "GENERAL",
        condition_sql: str = "",
        result_text: str = "",
        tables_related: str = "",
        priority: int = 50,
        target_rule_id: int | None = None,
        session_id: str | None = None,
        requested_by: str = "analista_agent",
    ) -> dict:
        clean_type = (proposal_type or "nueva_regla").strip().lower()
        if clean_type not in _PROPOSAL_TYPES:
            return {"ok": False, "error": "proposal_type no soportado"}

        title = (name or "").strip()
        detail = (description or "").strip()
        if not title or not detail:
            return {"ok": False, "error": "name y description son obligatorios"}

        now = self._now()
        proposal_id = f"KPRO-{uuid.uuid4().hex[:8].upper()}"
        similar = self.find_similar_rules(f"{title} {detail}", limit=10)
        payload = {
            "proposal_id": proposal_id,
            "status": "pending",
            "mode": self.mode,
            "proposal_type": clean_type,
            "name": title,
            "description": detail,
            "domain_code": (domain_code or "GENERAL").strip().upper(),
            "condition_sql": (condition_sql or "").strip(),
            "result_text": (result_text or "").strip(),
            "tables_related": (tables_related or "").strip(),
            "priority": max(1, min(int(priority), 100)),
            "target_rule_id": target_rule_id,
            "session_id": (session_id or "").strip() or None,
            "requested_by": (requested_by or "analista_agent").strip(),
            "similar_rules": similar,
            "persistence": None,
            "error": None,
            "version": 1,
            "last_idempotency_key": None,
            "created_at": now,
            "updated_at": now,
        }
        self.store.insert_knowledge_proposal(payload)

        if self.mode in ("auto", "directo"):
            applied = self.apply_proposal(
                proposal_id=proposal_id,
                bypass_auth=True,
                idempotency_key=f"auto-{proposal_id}",
            )
            return {
                "ok": bool(applied.get("ok")),
                "requires_auth": False,
                "applied": bool(applied.get("ok")),
                "proposal": self.get_proposal(proposal_id),
                "apply_result": applied,
            }

        return {
            "ok": True,
            "requires_auth": True,
            "applied": False,
            "proposal": self.get_proposal(proposal_id),
        }

    def get_proposal(self, proposal_id: str) -> dict | None:
        return self.store.get_knowledge_proposal((proposal_id or "").strip())

    def list_proposals(self, *, status: str | None = None, limit: int = 30) -> list[dict]:
        clean_status = (status or "").strip().lower() or None
        return self.store.list_knowledge_proposals(status=clean_status, limit=limit)

    def reject_proposal(self, *, proposal_id: str, reason: str = "") -> dict:
        pid = (proposal_id or "").strip()
        if not pid:
            return {"ok": False, "error": "proposal_id is required"}

        proposal = self.store.get_knowledge_proposal(pid)
        if not proposal:
            return {"ok": False, "error": "proposal_id no encontrado"}

        if proposal["status"] == "applied":
            return {"ok": False, "error": "La propuesta ya fue aplicada", "proposal": proposal}

        now = self._now()
        self.store.update_knowledge_proposal(
            pid,
            {
                "status": "rejected",
                "error": (reason or "").strip() or "Rechazada por gobierno de reglas",
                "updated_at": now,
                "version": int(proposal.get("version") or 1) + 1,
            },
        )
        return {"ok": True, "proposal": self.store.get_knowledge_proposal(pid)}

    def apply_proposal(
        self,
        *,
        proposal_id: str,
        auth_key: str | None = None,
        bypass_auth: bool = False,
        idempotency_key: str | None = None,
    ) -> dict:
        pid = (proposal_id or "").strip()
        if not pid:
            return {"ok": False, "error": "proposal_id is required"}

        if self.mode == "ceo" and not bypass_auth:
            if not self.ceo_auth_key:
                return {
                    "ok": False,
                    "error": "IA_DEV_CEO_AUTH_KEY no esta configurada",
                    "requires_auth": True,
                }
            if not self.validate_auth_key(auth_key):
                return {
                    "ok": False,
                    "error": "Clave de autorizacion invalida",
                    "requires_auth": True,
                }

        with transaction.atomic(using=self.db_alias):
            proposal = self.store.get_knowledge_proposal(pid, for_update=True)
            if not proposal:
                return {"ok": False, "error": "proposal_id no encontrado"}

            status = str(proposal.get("status") or "")
            if status == "applied":
                return {
                    "ok": True,
                    "proposal": proposal,
                    "persistence": proposal.get("persistence") or {},
                    "idempotent": True,
                }
            if status == "rejected":
                return {
                    "ok": False,
                    "error": "La propuesta fue rechazada y no puede aplicarse",
                    "proposal": proposal,
                }
            if status == "applying":
                return {
                    "ok": False,
                    "error": "La propuesta esta siendo aplicada por otro proceso",
                    "proposal": proposal,
                }
            if (
                idempotency_key
                and proposal.get("last_idempotency_key")
                and proposal.get("last_idempotency_key") == idempotency_key
                and proposal.get("persistence")
            ):
                return {
                    "ok": True,
                    "proposal": proposal,
                    "persistence": proposal.get("persistence"),
                    "idempotent": True,
                }

            next_version = int(proposal.get("version") or 1) + 1
            self.store.update_knowledge_proposal(
                pid,
                {
                    "status": "applying",
                    "updated_at": self._now(),
                    "version": next_version,
                    "last_idempotency_key": idempotency_key,
                },
            )

        proposal = self.store.get_knowledge_proposal(pid)
        if not proposal:
            return {"ok": False, "error": "proposal_id no encontrado"}

        if proposal["proposal_type"] == "actualizacion_regla":
            if not proposal["target_rule_id"]:
                result = {"error": "target_rule_id es obligatorio para actualizacion_regla"}
            else:
                result = self._apply_rule_update(proposal)
        else:
            result = self._apply_new_rule(proposal)

        final_updates = {
            "updated_at": self._now(),
            "persistence": result,
            "version": int(proposal.get("version") or 1) + 1,
        }
        if "error" in result:
            final_updates["status"] = "failed"
            final_updates["error"] = str(result.get("error"))
        else:
            final_updates["status"] = "applied"
            final_updates["error"] = None

        self.store.update_knowledge_proposal(pid, final_updates)
        final_proposal = self.store.get_knowledge_proposal(pid)
        return {
            "ok": "error" not in result,
            "proposal": final_proposal,
            "persistence": result,
        }

    def _apply_new_rule(self, proposal: dict) -> dict:
        schema = self._safe_schema()
        code = self._next_rule_code()
        default_condition = proposal.get("condition_sql") or "1=1 /* completar condicion */"
        default_result = proposal.get("result_text") or proposal.get("description")

        try:
            with transaction.atomic(using=self.db_alias):
                columns = self._get_rule_columns()
                domain_id = self._resolve_domain_id(str(proposal.get("domain_code") or "GENERAL"))
                insert_cols = [
                    "codigo",
                    "nombre",
                    "dominio_id",
                    "condicion_sql",
                    "resultado_funcional",
                    "prioridad",
                    "activo",
                ]
                insert_vals: list = [
                    code,
                    proposal.get("name"),
                    domain_id,
                    default_condition,
                    default_result,
                    int(proposal.get("priority") or 50),
                    1,
                ]

                if "tablas_relacionadas" in columns:
                    insert_cols.append("tablas_relacionadas")
                    insert_vals.append(proposal.get("tables_related") or "")
                if "agente_creador" in columns:
                    insert_cols.append("agente_creador")
                    insert_vals.append("IADevKnowledgeGovernance")
                if "estado" in columns:
                    insert_cols.append("estado")
                    insert_vals.append("activa")

                placeholders = ", ".join(["%s"] * len(insert_cols))
                sql = (
                    f"INSERT INTO {schema}.dd_reglas "
                    f"({', '.join(insert_cols)}) VALUES ({placeholders})"
                )

                with connections[self.db_alias].cursor() as cursor:
                    cursor.execute(sql, insert_vals)
                    rule_id = int(getattr(cursor, "lastrowid", 0) or 0)

            return {
                "rowcount": 1,
                "id_regla": rule_id,
                "codigo": code,
                "message": "Regla creada en ai_dictionary.dd_reglas",
            }
        except Exception as exc:
            return {"error": str(exc)}

    def _apply_rule_update(self, proposal: dict) -> dict:
        schema = self._safe_schema()
        try:
            with transaction.atomic(using=self.db_alias):
                columns = self._get_rule_columns()
                updates: list[str] = []
                params: list = []

                if proposal.get("condition_sql") and "condicion_sql" in columns:
                    updates.append("condicion_sql = %s")
                    params.append(proposal.get("condition_sql"))
                if proposal.get("result_text") and "resultado_funcional" in columns:
                    updates.append("resultado_funcional = %s")
                    params.append(proposal.get("result_text"))
                if proposal.get("tables_related") and "tablas_relacionadas" in columns:
                    updates.append("tablas_relacionadas = %s")
                    params.append(proposal.get("tables_related"))
                if "estado" in columns:
                    updates.append("estado = %s")
                    params.append("activa")

                if not updates:
                    return {"error": "No hay campos validos para actualizar en dd_reglas"}

                params.append(int(proposal.get("target_rule_id") or 0))
                sql = (
                    f"UPDATE {schema}.dd_reglas "
                    f"SET {', '.join(updates)} "
                    "WHERE id = %s"
                )

                with connections[self.db_alias].cursor() as cursor:
                    cursor.execute(sql, params)
                    rowcount = int(cursor.rowcount or 0)

            return {
                "rowcount": rowcount,
                "id_regla": int(proposal.get("target_rule_id") or 0),
                "message": "Regla actualizada en ai_dictionary.dd_reglas",
            }
        except Exception as exc:
            return {"error": str(exc)}
