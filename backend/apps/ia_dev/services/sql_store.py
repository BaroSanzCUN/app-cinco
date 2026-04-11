import json
import os
import threading
import time
from collections import defaultdict
from typing import Any

from django.db import connections


class IADevSqlStore:
    _init_lock = threading.Lock()
    _initialized_by_alias: set[str] = set()

    def __init__(self):
        self.db_alias = (os.getenv("IA_DEV_DB_ALIAS", "default") or "default").strip()

    def _execute(self, sql: str, params: list | tuple | None = None):
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params or [])

    def _fetchone(self, sql: str, params: list | tuple | None = None) -> tuple | None:
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params or [])
            return cursor.fetchone()

    def _fetchall(self, sql: str, params: list | tuple | None = None) -> list[tuple]:
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql, params or [])
            return cursor.fetchall()

    @staticmethod
    def _now() -> int:
        return int(time.time())

    def ensure_tables(self):
        if self.db_alias in self._initialized_by_alias:
            return
        with self._init_lock:
            if self.db_alias in self._initialized_by_alias:
                return

            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_session_memory (
                    session_id VARCHAR(64) PRIMARY KEY,
                    messages_json LONGTEXT NOT NULL,
                    context_json LONGTEXT NOT NULL,
                    trim_events INT NOT NULL DEFAULT 0,
                    updated_at BIGINT NOT NULL
                )
                """
            )
            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_tickets (
                    ticket_id VARCHAR(32) PRIMARY KEY,
                    category VARCHAR(64) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    session_id VARCHAR(64) NULL,
                    created_at BIGINT NOT NULL
                )
                """
            )
            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_knowledge_proposals (
                    proposal_id VARCHAR(32) PRIMARY KEY,
                    status VARCHAR(32) NOT NULL,
                    mode VARCHAR(16) NOT NULL,
                    proposal_type VARCHAR(32) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    domain_code VARCHAR(64) NOT NULL,
                    condition_sql TEXT NOT NULL,
                    result_text TEXT NOT NULL,
                    tables_related TEXT NOT NULL,
                    priority INT NOT NULL,
                    target_rule_id INT NULL,
                    session_id VARCHAR(64) NULL,
                    requested_by VARCHAR(64) NOT NULL,
                    similar_rules_json LONGTEXT NOT NULL,
                    persistence_json LONGTEXT NULL,
                    error TEXT NULL,
                    version INT NOT NULL DEFAULT 1,
                    last_idempotency_key VARCHAR(120) NULL,
                    created_at BIGINT NOT NULL,
                    updated_at BIGINT NOT NULL
                )
                """
            )
            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_async_jobs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    job_id VARCHAR(40) NOT NULL UNIQUE,
                    job_type VARCHAR(64) NOT NULL,
                    status VARCHAR(24) NOT NULL,
                    payload_json LONGTEXT NOT NULL,
                    result_json LONGTEXT NULL,
                    error TEXT NULL,
                    idempotency_key VARCHAR(120) NULL UNIQUE,
                    created_at BIGINT NOT NULL,
                    updated_at BIGINT NOT NULL,
                    run_after BIGINT NOT NULL DEFAULT 0
                )
                """
            )
            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_observability_events (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    event_type VARCHAR(80) NOT NULL,
                    source VARCHAR(80) NOT NULL,
                    duration_ms INT NULL,
                    tokens_in INT NULL,
                    tokens_out INT NULL,
                    cost_usd DECIMAL(14,8) NULL,
                    meta_json LONGTEXT NULL,
                    created_at BIGINT NOT NULL
                )
                """
            )
            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_user_memory (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_key VARCHAR(128) NOT NULL,
                    memory_key VARCHAR(120) NOT NULL,
                    memory_value_json LONGTEXT NOT NULL,
                    sensitivity VARCHAR(16) NOT NULL DEFAULT 'medium',
                    source VARCHAR(40) NOT NULL DEFAULT 'api',
                    confidence DECIMAL(6,5) NOT NULL DEFAULT 1.00000,
                    expires_at BIGINT NULL,
                    created_at BIGINT NOT NULL,
                    updated_at BIGINT NOT NULL,
                    UNIQUE KEY uq_ia_dev_user_memory (user_key, memory_key),
                    KEY idx_ia_dev_user_memory_user (user_key),
                    KEY idx_ia_dev_user_memory_updated (updated_at)
                )
                """
            )
            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_business_memory (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    domain_code VARCHAR(64) NOT NULL,
                    capability_id VARCHAR(120) NOT NULL,
                    memory_key VARCHAR(120) NOT NULL,
                    memory_value_json LONGTEXT NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    source_type VARCHAR(40) NOT NULL DEFAULT 'manual',
                    version INT NOT NULL DEFAULT 1,
                    approved_by VARCHAR(64) NULL,
                    approved_at BIGINT NULL,
                    created_at BIGINT NOT NULL,
                    updated_at BIGINT NOT NULL,
                    UNIQUE KEY uq_ia_dev_business_memory (domain_code, capability_id, memory_key),
                    KEY idx_ia_dev_business_memory_domain (domain_code),
                    KEY idx_ia_dev_business_memory_capability (capability_id),
                    KEY idx_ia_dev_business_memory_status (status)
                )
                """
            )
            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_learned_memory_proposals (
                    proposal_id VARCHAR(40) PRIMARY KEY,
                    scope VARCHAR(20) NOT NULL,
                    status VARCHAR(24) NOT NULL,
                    proposer_user_key VARCHAR(128) NOT NULL,
                    source_run_id VARCHAR(64) NULL,
                    candidate_key VARCHAR(120) NOT NULL,
                    candidate_value_json LONGTEXT NOT NULL,
                    reason TEXT NULL,
                    sensitivity VARCHAR(16) NOT NULL DEFAULT 'medium',
                    domain_code VARCHAR(64) NULL,
                    capability_id VARCHAR(120) NULL,
                    policy_action VARCHAR(24) NULL,
                    policy_id VARCHAR(80) NULL,
                    idempotency_key VARCHAR(120) NULL UNIQUE,
                    error TEXT NULL,
                    version INT NOT NULL DEFAULT 1,
                    created_at BIGINT NOT NULL,
                    updated_at BIGINT NOT NULL,
                    KEY idx_ia_dev_lmp_status (status),
                    KEY idx_ia_dev_lmp_scope (scope),
                    KEY idx_ia_dev_lmp_created (created_at)
                )
                """
            )
            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_learned_memory_approvals (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    proposal_id VARCHAR(40) NOT NULL,
                    action VARCHAR(16) NOT NULL,
                    actor_user_key VARCHAR(128) NOT NULL,
                    actor_role VARCHAR(64) NOT NULL,
                    comment TEXT NULL,
                    created_at BIGINT NOT NULL,
                    KEY idx_ia_dev_lma_proposal (proposal_id),
                    KEY idx_ia_dev_lma_created (created_at)
                )
                """
            )
            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_workflow_state (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    workflow_type VARCHAR(64) NOT NULL,
                    workflow_key VARCHAR(120) NOT NULL UNIQUE,
                    status VARCHAR(24) NOT NULL,
                    state_json LONGTEXT NOT NULL,
                    retry_count INT NOT NULL DEFAULT 0,
                    lock_version INT NOT NULL DEFAULT 1,
                    next_retry_at BIGINT NULL,
                    last_error TEXT NULL,
                    created_at BIGINT NOT NULL,
                    updated_at BIGINT NOT NULL,
                    KEY idx_ia_dev_workflow_type (workflow_type),
                    KEY idx_ia_dev_workflow_status (status)
                )
                """
            )
            self._execute(
                """
                CREATE TABLE IF NOT EXISTS ia_dev_memory_audit_trail (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    event_type VARCHAR(64) NOT NULL,
                    memory_scope VARCHAR(20) NOT NULL,
                    entity_key VARCHAR(140) NOT NULL,
                    action VARCHAR(24) NOT NULL,
                    actor_type VARCHAR(24) NOT NULL,
                    actor_key VARCHAR(128) NOT NULL,
                    run_id VARCHAR(64) NULL,
                    trace_id VARCHAR(64) NULL,
                    before_json LONGTEXT NULL,
                    after_json LONGTEXT NULL,
                    meta_json LONGTEXT NULL,
                    created_at BIGINT NOT NULL,
                    KEY idx_ia_dev_mat_scope (memory_scope),
                    KEY idx_ia_dev_mat_entity (entity_key),
                    KEY idx_ia_dev_mat_run (run_id),
                    KEY idx_ia_dev_mat_trace (trace_id),
                    KEY idx_ia_dev_mat_created (created_at)
                )
                """
            )
            self._initialized_by_alias.add(self.db_alias)

    @staticmethod
    def _to_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _from_json(raw: str | None, default: Any):
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default

    # Session memory
    def upsert_session_memory(
        self,
        *,
        session_id: str,
        messages: list[dict],
        context: dict,
        trim_events: int,
        updated_at: int | None = None,
    ):
        self.ensure_tables()
        ts = int(updated_at or self._now())
        existing = self._fetchone(
            "SELECT session_id FROM ia_dev_session_memory WHERE session_id = %s LIMIT 1",
            [session_id],
        )
        if existing:
            self._execute(
                """
                UPDATE ia_dev_session_memory
                SET messages_json = %s,
                    context_json = %s,
                    trim_events = %s,
                    updated_at = %s
                WHERE session_id = %s
                """,
                [
                    self._to_json(messages),
                    self._to_json(context),
                    int(trim_events),
                    ts,
                    session_id,
                ],
            )
            return

        self._execute(
            """
            INSERT INTO ia_dev_session_memory
                (session_id, messages_json, context_json, trim_events, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                session_id,
                self._to_json(messages),
                self._to_json(context),
                int(trim_events),
                ts,
            ],
        )

    def get_session_memory(self, session_id: str) -> dict | None:
        self.ensure_tables()
        row = self._fetchone(
            """
            SELECT session_id, messages_json, context_json, trim_events, updated_at
            FROM ia_dev_session_memory
            WHERE session_id = %s
            LIMIT 1
            """,
            [session_id],
        )
        if not row:
            return None
        return {
            "session_id": str(row[0]),
            "messages": self._from_json(row[1], []),
            "context": self._from_json(row[2], {}),
            "trim_events": int(row[3] or 0),
            "updated_at": int(row[4] or 0),
        }

    # User memory
    def upsert_user_memory(
        self,
        *,
        user_key: str,
        memory_key: str,
        memory_value: Any,
        sensitivity: str = "medium",
        source: str = "api",
        confidence: float = 1.0,
        expires_at: int | None = None,
    ):
        self.ensure_tables()
        now = self._now()
        existing = self._fetchone(
            """
            SELECT id
            FROM ia_dev_user_memory
            WHERE user_key = %s
              AND memory_key = %s
            LIMIT 1
            """,
            [user_key, memory_key],
        )
        if existing:
            self._execute(
                """
                UPDATE ia_dev_user_memory
                SET memory_value_json = %s,
                    sensitivity = %s,
                    source = %s,
                    confidence = %s,
                    expires_at = %s,
                    updated_at = %s
                WHERE user_key = %s
                  AND memory_key = %s
                """,
                [
                    self._to_json(memory_value),
                    sensitivity[:16],
                    source[:40],
                    max(0.0, min(float(confidence), 1.0)),
                    expires_at,
                    now,
                    user_key,
                    memory_key,
                ],
            )
            return

        self._execute(
            """
            INSERT INTO ia_dev_user_memory
                (user_key, memory_key, memory_value_json, sensitivity, source, confidence, expires_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                user_key,
                memory_key,
                self._to_json(memory_value),
                sensitivity[:16],
                source[:40],
                max(0.0, min(float(confidence), 1.0)),
                expires_at,
                now,
                now,
            ],
        )

    def get_user_memory_entry(self, *, user_key: str, memory_key: str) -> dict | None:
        self.ensure_tables()
        row = self._fetchone(
            """
            SELECT id, user_key, memory_key, memory_value_json, sensitivity, source, confidence, expires_at, created_at, updated_at
            FROM ia_dev_user_memory
            WHERE user_key = %s
              AND memory_key = %s
            LIMIT 1
            """,
            [user_key, memory_key],
        )
        if not row:
            return None
        return {
            "id": int(row[0]),
            "user_key": str(row[1] or ""),
            "memory_key": str(row[2] or ""),
            "memory_value": self._from_json(row[3], None),
            "sensitivity": str(row[4] or "medium"),
            "source": str(row[5] or "api"),
            "confidence": float(row[6] or 0.0),
            "expires_at": int(row[7]) if row[7] is not None else None,
            "created_at": int(row[8] or 0),
            "updated_at": int(row[9] or 0),
        }

    def list_user_memory(self, *, user_key: str, limit: int = 100) -> list[dict]:
        self.ensure_tables()
        safe_limit = max(1, min(int(limit), 500))
        now = self._now()
        rows = self._fetchall(
            """
            SELECT id, user_key, memory_key, memory_value_json, sensitivity, source, confidence, expires_at, created_at, updated_at
            FROM ia_dev_user_memory
            WHERE user_key = %s
              AND (expires_at IS NULL OR expires_at >= %s)
            ORDER BY updated_at DESC
            LIMIT %s
            """,
            [user_key, now, safe_limit],
        )
        return [
            {
                "id": int(row[0]),
                "user_key": str(row[1] or ""),
                "memory_key": str(row[2] or ""),
                "memory_value": self._from_json(row[3], None),
                "sensitivity": str(row[4] or "medium"),
                "source": str(row[5] or "api"),
                "confidence": float(row[6] or 0.0),
                "expires_at": int(row[7]) if row[7] is not None else None,
                "created_at": int(row[8] or 0),
                "updated_at": int(row[9] or 0),
            }
            for row in rows
        ]

    # Business memory
    def upsert_business_memory(
        self,
        *,
        domain_code: str,
        capability_id: str,
        memory_key: str,
        memory_value: Any,
        status: str = "active",
        source_type: str = "manual",
        approved_by: str | None = None,
        approved_at: int | None = None,
    ):
        self.ensure_tables()
        now = self._now()
        existing = self._fetchone(
            """
            SELECT id, version
            FROM ia_dev_business_memory
            WHERE domain_code = %s
              AND capability_id = %s
              AND memory_key = %s
            LIMIT 1
            """,
            [domain_code, capability_id, memory_key],
        )
        if existing:
            next_version = int(existing[1] or 1) + 1
            self._execute(
                """
                UPDATE ia_dev_business_memory
                SET memory_value_json = %s,
                    status = %s,
                    source_type = %s,
                    version = %s,
                    approved_by = %s,
                    approved_at = %s,
                    updated_at = %s
                WHERE id = %s
                """,
                [
                    self._to_json(memory_value),
                    status[:20],
                    source_type[:40],
                    next_version,
                    approved_by,
                    approved_at,
                    now,
                    int(existing[0]),
                ],
            )
            return

        self._execute(
            """
            INSERT INTO ia_dev_business_memory
                (domain_code, capability_id, memory_key, memory_value_json, status, source_type, version, approved_by, approved_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s)
            """,
            [
                domain_code[:64],
                capability_id[:120],
                memory_key[:120],
                self._to_json(memory_value),
                status[:20],
                source_type[:40],
                approved_by,
                approved_at,
                now,
                now,
            ],
        )

    def get_business_memory_entry(
        self,
        *,
        domain_code: str,
        capability_id: str,
        memory_key: str,
    ) -> dict | None:
        self.ensure_tables()
        row = self._fetchone(
            """
            SELECT id, domain_code, capability_id, memory_key, memory_value_json, status, source_type, version, approved_by, approved_at, created_at, updated_at
            FROM ia_dev_business_memory
            WHERE domain_code = %s
              AND capability_id = %s
              AND memory_key = %s
            LIMIT 1
            """,
            [domain_code, capability_id, memory_key],
        )
        if not row:
            return None
        return {
            "id": int(row[0]),
            "domain_code": str(row[1] or ""),
            "capability_id": str(row[2] or ""),
            "memory_key": str(row[3] or ""),
            "memory_value": self._from_json(row[4], None),
            "status": str(row[5] or ""),
            "source_type": str(row[6] or ""),
            "version": int(row[7] or 1),
            "approved_by": str(row[8]) if row[8] else None,
            "approved_at": int(row[9]) if row[9] is not None else None,
            "created_at": int(row[10] or 0),
            "updated_at": int(row[11] or 0),
        }

    def list_business_memory(
        self,
        *,
        domain_code: str | None = None,
        capability_id: str | None = None,
        status: str | None = "active",
        limit: int = 100,
    ) -> list[dict]:
        self.ensure_tables()
        safe_limit = max(1, min(int(limit), 500))
        where: list[str] = ["1 = 1"]
        params: list[Any] = []
        if domain_code:
            where.append("domain_code = %s")
            params.append(domain_code)
        if capability_id:
            where.append("capability_id = %s")
            params.append(capability_id)
        if status:
            where.append("status = %s")
            params.append(status)
        params.append(safe_limit)
        rows = self._fetchall(
            f"""
            SELECT id, domain_code, capability_id, memory_key, memory_value_json, status, source_type, version, approved_by, approved_at, created_at, updated_at
            FROM ia_dev_business_memory
            WHERE {" AND ".join(where)}
            ORDER BY updated_at DESC
            LIMIT %s
            """,
            params,
        )
        return [
            {
                "id": int(row[0]),
                "domain_code": str(row[1] or ""),
                "capability_id": str(row[2] or ""),
                "memory_key": str(row[3] or ""),
                "memory_value": self._from_json(row[4], None),
                "status": str(row[5] or ""),
                "source_type": str(row[6] or ""),
                "version": int(row[7] or 1),
                "approved_by": str(row[8]) if row[8] else None,
                "approved_at": int(row[9]) if row[9] is not None else None,
                "created_at": int(row[10] or 0),
                "updated_at": int(row[11] or 0),
            }
            for row in rows
        ]

    # Learned memory proposals
    def insert_learned_memory_proposal(self, proposal: dict):
        self.ensure_tables()
        self._execute(
            """
            INSERT INTO ia_dev_learned_memory_proposals
                (proposal_id, scope, status, proposer_user_key, source_run_id, candidate_key, candidate_value_json, reason,
                 sensitivity, domain_code, capability_id, policy_action, policy_id, idempotency_key, error, version, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                proposal["proposal_id"],
                proposal["scope"],
                proposal.get("status", "pending"),
                proposal.get("proposer_user_key"),
                proposal.get("source_run_id"),
                proposal.get("candidate_key"),
                self._to_json(proposal.get("candidate_value")),
                proposal.get("reason"),
                proposal.get("sensitivity", "medium"),
                proposal.get("domain_code"),
                proposal.get("capability_id"),
                proposal.get("policy_action"),
                proposal.get("policy_id"),
                proposal.get("idempotency_key"),
                proposal.get("error"),
                int(proposal.get("version") or 1),
                int(proposal.get("created_at") or self._now()),
                int(proposal.get("updated_at") or self._now()),
            ],
        )

    def get_learned_memory_proposal(self, proposal_id: str, *, for_update: bool = False) -> dict | None:
        self.ensure_tables()
        query = (
            """
            SELECT proposal_id, scope, status, proposer_user_key, source_run_id, candidate_key, candidate_value_json, reason,
                   sensitivity, domain_code, capability_id, policy_action, policy_id, idempotency_key, error, version, created_at, updated_at
            FROM ia_dev_learned_memory_proposals
            WHERE proposal_id = %s
            LIMIT 1
            """
            + (" FOR UPDATE" if for_update else "")
        )
        row = self._fetchone(query, [proposal_id])
        if not row:
            return None
        return {
            "proposal_id": str(row[0] or ""),
            "scope": str(row[1] or ""),
            "status": str(row[2] or ""),
            "proposer_user_key": str(row[3] or ""),
            "source_run_id": str(row[4]) if row[4] else None,
            "candidate_key": str(row[5] or ""),
            "candidate_value": self._from_json(row[6], None),
            "reason": str(row[7]) if row[7] else "",
            "sensitivity": str(row[8] or "medium"),
            "domain_code": str(row[9]) if row[9] else None,
            "capability_id": str(row[10]) if row[10] else None,
            "policy_action": str(row[11]) if row[11] else None,
            "policy_id": str(row[12]) if row[12] else None,
            "idempotency_key": str(row[13]) if row[13] else None,
            "error": str(row[14]) if row[14] else None,
            "version": int(row[15] or 1),
            "created_at": int(row[16] or 0),
            "updated_at": int(row[17] or 0),
        }

    def get_learned_memory_proposal_by_idempotency(self, idempotency_key: str) -> dict | None:
        self.ensure_tables()
        if not str(idempotency_key or "").strip():
            return None
        row = self._fetchone(
            """
            SELECT proposal_id
            FROM ia_dev_learned_memory_proposals
            WHERE idempotency_key = %s
            LIMIT 1
            """,
            [idempotency_key],
        )
        if not row:
            return None
        return self.get_learned_memory_proposal(str(row[0] or ""))

    def list_learned_memory_proposals(
        self,
        *,
        status: str | None = None,
        scope: str | None = None,
        proposer_user_key: str | None = None,
        limit: int = 30,
    ) -> list[dict]:
        self.ensure_tables()
        safe_limit = max(1, min(int(limit), 200))
        where: list[str] = ["1 = 1"]
        params: list[Any] = []
        if status:
            where.append("status = %s")
            params.append(status)
        if scope:
            where.append("scope = %s")
            params.append(scope)
        if proposer_user_key:
            where.append("proposer_user_key = %s")
            params.append(proposer_user_key)
        params.append(safe_limit)
        rows = self._fetchall(
            f"""
            SELECT proposal_id
            FROM ia_dev_learned_memory_proposals
            WHERE {" AND ".join(where)}
            ORDER BY created_at DESC
            LIMIT %s
            """,
            params,
        )
        result: list[dict] = []
        for row in rows:
            proposal = self.get_learned_memory_proposal(str(row[0]))
            if proposal:
                result.append(proposal)
        return result

    def update_learned_memory_proposal(self, proposal_id: str, updates: dict):
        self.ensure_tables()
        allowed = {
            "scope",
            "status",
            "reason",
            "sensitivity",
            "domain_code",
            "capability_id",
            "policy_action",
            "policy_id",
            "error",
            "version",
            "updated_at",
            "candidate_value",
        }
        sets: list[str] = []
        params: list[Any] = []
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "candidate_value":
                sets.append("candidate_value_json = %s")
                params.append(self._to_json(value))
            else:
                sets.append(f"{key} = %s")
                params.append(value)
        if not sets:
            return
        params.append(proposal_id)
        self._execute(
            f"""
            UPDATE ia_dev_learned_memory_proposals
            SET {", ".join(sets)}
            WHERE proposal_id = %s
            """,
            params,
        )

    def insert_learned_memory_approval(self, approval: dict):
        self.ensure_tables()
        self._execute(
            """
            INSERT INTO ia_dev_learned_memory_approvals
                (proposal_id, action, actor_user_key, actor_role, comment, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                approval.get("proposal_id"),
                approval.get("action"),
                approval.get("actor_user_key"),
                approval.get("actor_role"),
                approval.get("comment"),
                int(approval.get("created_at") or self._now()),
            ],
        )

    def list_learned_memory_approvals(self, *, proposal_id: str, limit: int = 20) -> list[dict]:
        self.ensure_tables()
        safe_limit = max(1, min(int(limit), 200))
        rows = self._fetchall(
            """
            SELECT id, proposal_id, action, actor_user_key, actor_role, comment, created_at
            FROM ia_dev_learned_memory_approvals
            WHERE proposal_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            [proposal_id, safe_limit],
        )
        return [
            {
                "id": int(row[0]),
                "proposal_id": str(row[1] or ""),
                "action": str(row[2] or ""),
                "actor_user_key": str(row[3] or ""),
                "actor_role": str(row[4] or ""),
                "comment": str(row[5]) if row[5] else "",
                "created_at": int(row[6] or 0),
            }
            for row in rows
        ]

    # Workflow state
    def upsert_workflow_state(
        self,
        *,
        workflow_type: str,
        workflow_key: str,
        status: str,
        state: dict,
        retry_count: int = 0,
        lock_version: int = 1,
        next_retry_at: int | None = None,
        last_error: str | None = None,
    ):
        self.ensure_tables()
        now = self._now()
        existing = self._fetchone(
            """
            SELECT id
            FROM ia_dev_workflow_state
            WHERE workflow_key = %s
            LIMIT 1
            """,
            [workflow_key],
        )
        if existing:
            self._execute(
                """
                UPDATE ia_dev_workflow_state
                SET workflow_type = %s,
                    status = %s,
                    state_json = %s,
                    retry_count = %s,
                    lock_version = %s,
                    next_retry_at = %s,
                    last_error = %s,
                    updated_at = %s
                WHERE workflow_key = %s
                """,
                [
                    workflow_type,
                    status,
                    self._to_json(state),
                    int(retry_count),
                    int(lock_version),
                    next_retry_at,
                    last_error,
                    now,
                    workflow_key,
                ],
            )
            return
        self._execute(
            """
            INSERT INTO ia_dev_workflow_state
                (workflow_type, workflow_key, status, state_json, retry_count, lock_version, next_retry_at, last_error, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                workflow_type,
                workflow_key,
                status,
                self._to_json(state),
                int(retry_count),
                int(lock_version),
                next_retry_at,
                last_error,
                now,
                now,
            ],
        )

    def get_workflow_state(self, workflow_key: str) -> dict | None:
        self.ensure_tables()
        row = self._fetchone(
            """
            SELECT id, workflow_type, workflow_key, status, state_json, retry_count, lock_version, next_retry_at, last_error, created_at, updated_at
            FROM ia_dev_workflow_state
            WHERE workflow_key = %s
            LIMIT 1
            """,
            [workflow_key],
        )
        if not row:
            return None
        return {
            "id": int(row[0]),
            "workflow_type": str(row[1] or ""),
            "workflow_key": str(row[2] or ""),
            "status": str(row[3] or ""),
            "state": self._from_json(row[4], {}),
            "retry_count": int(row[5] or 0),
            "lock_version": int(row[6] or 1),
            "next_retry_at": int(row[7]) if row[7] is not None else None,
            "last_error": str(row[8]) if row[8] else None,
            "created_at": int(row[9] or 0),
            "updated_at": int(row[10] or 0),
        }

    # Memory audit
    def insert_memory_audit_event(
        self,
        *,
        event_type: str,
        memory_scope: str,
        entity_key: str,
        action: str,
        actor_type: str,
        actor_key: str,
        run_id: str | None = None,
        trace_id: str | None = None,
        before: Any = None,
        after: Any = None,
        meta: dict | None = None,
    ):
        self.ensure_tables()
        self._execute(
            """
            INSERT INTO ia_dev_memory_audit_trail
                (event_type, memory_scope, entity_key, action, actor_type, actor_key, run_id, trace_id, before_json, after_json, meta_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (event_type or "")[:64],
                (memory_scope or "")[:20],
                (entity_key or "")[:140],
                (action or "")[:24],
                (actor_type or "")[:24],
                (actor_key or "")[:128],
                (run_id or "")[:64] or None,
                (trace_id or "")[:64] or None,
                self._to_json(before) if before is not None else None,
                self._to_json(after) if after is not None else None,
                self._to_json(meta or {}),
                self._now(),
            ],
        )

    def list_memory_audit_events(
        self,
        *,
        memory_scope: str | None = None,
        entity_key: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        self.ensure_tables()
        safe_limit = max(1, min(int(limit), 1000))
        where: list[str] = ["1 = 1"]
        params: list[Any] = []
        if memory_scope:
            where.append("memory_scope = %s")
            params.append(memory_scope)
        if entity_key:
            where.append("entity_key = %s")
            params.append(entity_key)
        params.append(safe_limit)
        rows = self._fetchall(
            f"""
            SELECT id, event_type, memory_scope, entity_key, action, actor_type, actor_key, run_id, trace_id, before_json, after_json, meta_json, created_at
            FROM ia_dev_memory_audit_trail
            WHERE {" AND ".join(where)}
            ORDER BY id DESC
            LIMIT %s
            """,
            params,
        )
        return [
            {
                "id": int(row[0]),
                "event_type": str(row[1] or ""),
                "memory_scope": str(row[2] or ""),
                "entity_key": str(row[3] or ""),
                "action": str(row[4] or ""),
                "actor_type": str(row[5] or ""),
                "actor_key": str(row[6] or ""),
                "run_id": str(row[7]) if row[7] else None,
                "trace_id": str(row[8]) if row[8] else None,
                "before": self._from_json(row[9], None),
                "after": self._from_json(row[10], None),
                "meta": self._from_json(row[11], {}),
                "created_at": int(row[12] or 0),
            }
            for row in rows
        ]

    # Tickets
    def insert_ticket(
        self,
        *,
        ticket_id: str,
        category: str,
        title: str,
        description: str,
        session_id: str | None,
        created_at: int,
    ):
        self.ensure_tables()
        self._execute(
            """
            INSERT INTO ia_dev_tickets
                (ticket_id, category, title, description, session_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [ticket_id, category, title, description, session_id, int(created_at)],
        )

    def get_ticket(self, ticket_id: str) -> dict | None:
        self.ensure_tables()
        row = self._fetchone(
            """
            SELECT ticket_id, category, title, description, session_id, created_at
            FROM ia_dev_tickets
            WHERE ticket_id = %s
            LIMIT 1
            """,
            [ticket_id],
        )
        if not row:
            return None
        return {
            "ticket_id": str(row[0]),
            "category": str(row[1] or ""),
            "title": str(row[2] or ""),
            "description": str(row[3] or ""),
            "session_id": str(row[4]) if row[4] else None,
            "created_at": int(row[5] or 0),
        }

    # Knowledge proposals
    def insert_knowledge_proposal(self, proposal: dict):
        self.ensure_tables()
        self._execute(
            """
            INSERT INTO ia_dev_knowledge_proposals (
                proposal_id, status, mode, proposal_type, name, description, domain_code,
                condition_sql, result_text, tables_related, priority, target_rule_id,
                session_id, requested_by, similar_rules_json, persistence_json, error,
                version, last_idempotency_key, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                proposal["proposal_id"],
                proposal["status"],
                proposal["mode"],
                proposal["proposal_type"],
                proposal["name"],
                proposal["description"],
                proposal["domain_code"],
                proposal["condition_sql"],
                proposal["result_text"],
                proposal["tables_related"],
                int(proposal["priority"]),
                proposal.get("target_rule_id"),
                proposal.get("session_id"),
                proposal["requested_by"],
                self._to_json(proposal.get("similar_rules") or []),
                self._to_json(proposal.get("persistence")) if proposal.get("persistence") is not None else None,
                proposal.get("error"),
                int(proposal.get("version") or 1),
                proposal.get("last_idempotency_key"),
                int(proposal["created_at"]),
                int(proposal["updated_at"]),
            ],
        )

    def get_knowledge_proposal(self, proposal_id: str, *, for_update: bool = False) -> dict | None:
        self.ensure_tables()
        query = (
            """
            SELECT proposal_id, status, mode, proposal_type, name, description, domain_code,
                   condition_sql, result_text, tables_related, priority, target_rule_id,
                   session_id, requested_by, similar_rules_json, persistence_json, error,
                   version, last_idempotency_key, created_at, updated_at
            FROM ia_dev_knowledge_proposals
            WHERE proposal_id = %s
            LIMIT 1
            """
            + (" FOR UPDATE" if for_update else "")
        )
        row = self._fetchone(query, [proposal_id])
        if not row:
            return None
        return {
            "proposal_id": str(row[0]),
            "status": str(row[1] or ""),
            "mode": str(row[2] or ""),
            "proposal_type": str(row[3] or ""),
            "name": str(row[4] or ""),
            "description": str(row[5] or ""),
            "domain_code": str(row[6] or ""),
            "condition_sql": str(row[7] or ""),
            "result_text": str(row[8] or ""),
            "tables_related": str(row[9] or ""),
            "priority": int(row[10] or 0),
            "target_rule_id": int(row[11]) if row[11] is not None else None,
            "session_id": str(row[12]) if row[12] else None,
            "requested_by": str(row[13] or ""),
            "similar_rules": self._from_json(row[14], []),
            "persistence": self._from_json(row[15], None),
            "error": str(row[16]) if row[16] else None,
            "version": int(row[17] or 1),
            "last_idempotency_key": str(row[18]) if row[18] else None,
            "created_at": int(row[19] or 0),
            "updated_at": int(row[20] or 0),
        }

    def list_knowledge_proposals(self, *, status: str | None = None, limit: int = 30) -> list[dict]:
        self.ensure_tables()
        safe_limit = max(1, min(int(limit), 100))
        if status:
            rows = self._fetchall(
                """
                SELECT proposal_id
                FROM ia_dev_knowledge_proposals
                WHERE status = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                [status, safe_limit],
            )
        else:
            rows = self._fetchall(
                """
                SELECT proposal_id
                FROM ia_dev_knowledge_proposals
                ORDER BY created_at DESC
                LIMIT %s
                """,
                [safe_limit],
            )
        result: list[dict] = []
        for row in rows:
            item = self.get_knowledge_proposal(str(row[0]))
            if item:
                result.append(item)
        return result

    def update_knowledge_proposal(self, proposal_id: str, updates: dict):
        self.ensure_tables()
        allowed = {
            "status",
            "condition_sql",
            "result_text",
            "tables_related",
            "priority",
            "target_rule_id",
            "similar_rules",
            "persistence",
            "error",
            "version",
            "last_idempotency_key",
            "updated_at",
        }
        sets: list[str] = []
        params: list = []
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "similar_rules":
                sets.append("similar_rules_json = %s")
                params.append(self._to_json(value or []))
            elif key == "persistence":
                sets.append("persistence_json = %s")
                params.append(self._to_json(value) if value is not None else None)
            else:
                sets.append(f"{key} = %s")
                params.append(value)
        if not sets:
            return
        params.append(proposal_id)
        self._execute(
            f"""
            UPDATE ia_dev_knowledge_proposals
            SET {", ".join(sets)}
            WHERE proposal_id = %s
            """,
            params,
        )

    # Async jobs
    def insert_async_job(
        self,
        *,
        job_id: str,
        job_type: str,
        payload: dict,
        status: str,
        idempotency_key: str | None,
        run_after: int,
    ):
        self.ensure_tables()
        now = self._now()
        self._execute(
            """
            INSERT INTO ia_dev_async_jobs
                (job_id, job_type, status, payload_json, result_json, error, idempotency_key, created_at, updated_at, run_after)
            VALUES (%s, %s, %s, %s, NULL, NULL, %s, %s, %s, %s)
            """,
            [
                job_id,
                job_type,
                status,
                self._to_json(payload),
                idempotency_key,
                now,
                now,
                int(run_after),
            ],
        )

    def get_async_job_by_idempotency(self, idempotency_key: str) -> dict | None:
        self.ensure_tables()
        row = self._fetchone(
            """
            SELECT job_id, job_type, status, payload_json, result_json, error, idempotency_key, created_at, updated_at, run_after
            FROM ia_dev_async_jobs
            WHERE idempotency_key = %s
            LIMIT 1
            """,
            [idempotency_key],
        )
        return self._map_async_job(row)

    def list_pending_async_jobs(self, *, limit: int = 20) -> list[dict]:
        self.ensure_tables()
        now = self._now()
        rows = self._fetchall(
            """
            SELECT job_id, job_type, status, payload_json, result_json, error, idempotency_key, created_at, updated_at, run_after
            FROM ia_dev_async_jobs
            WHERE status = 'pending'
              AND run_after <= %s
            ORDER BY created_at ASC
            LIMIT %s
            """,
            [now, max(1, min(int(limit), 200))],
        )
        return [item for item in (self._map_async_job(row) for row in rows) if item]

    def claim_pending_async_jobs(self, *, limit: int = 20) -> list[dict]:
        self.ensure_tables()
        now = self._now()
        rows = self._fetchall(
            """
            SELECT job_id
            FROM ia_dev_async_jobs
            WHERE status = 'pending'
              AND run_after <= %s
            ORDER BY created_at ASC
            LIMIT %s
            """,
            [now, max(1, min(int(limit), 200))],
        )
        claimed: list[dict] = []
        for row in rows:
            job_id = str(row[0] or "").strip()
            if not job_id:
                continue
            with connections[self.db_alias].cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE ia_dev_async_jobs
                    SET status = 'running',
                        updated_at = %s
                    WHERE job_id = %s
                      AND status = 'pending'
                    """,
                    [self._now(), job_id],
                )
                if int(cursor.rowcount or 0) != 1:
                    continue
            item = self.get_async_job(job_id)
            if item:
                claimed.append(item)
        return claimed

    def get_async_job(self, job_id: str) -> dict | None:
        self.ensure_tables()
        row = self._fetchone(
            """
            SELECT job_id, job_type, status, payload_json, result_json, error, idempotency_key, created_at, updated_at, run_after
            FROM ia_dev_async_jobs
            WHERE job_id = %s
            LIMIT 1
            """,
            [job_id],
        )
        return self._map_async_job(row)

    def update_async_job(
        self,
        *,
        job_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ):
        self.ensure_tables()
        now = self._now()
        self._execute(
            """
            UPDATE ia_dev_async_jobs
            SET status = %s,
                result_json = %s,
                error = %s,
                updated_at = %s
            WHERE job_id = %s
            """,
            [
                status,
                self._to_json(result) if result is not None else None,
                error,
                now,
                job_id,
            ],
        )

    def _map_async_job(self, row: tuple | None) -> dict | None:
        if not row:
            return None
        return {
            "job_id": str(row[0]),
            "job_type": str(row[1] or ""),
            "status": str(row[2] or ""),
            "payload": self._from_json(row[3], {}),
            "result": self._from_json(row[4], None),
            "error": str(row[5]) if row[5] else None,
            "idempotency_key": str(row[6]) if row[6] else None,
            "created_at": int(row[7] or 0),
            "updated_at": int(row[8] or 0),
            "run_after": int(row[9] or 0),
        }

    # Observability
    def insert_observability_event(
        self,
        *,
        event_type: str,
        source: str,
        duration_ms: int | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        cost_usd: float | None = None,
        meta: dict | None = None,
    ):
        self.ensure_tables()
        self._execute(
            """
            INSERT INTO ia_dev_observability_events
                (event_type, source, duration_ms, tokens_in, tokens_out, cost_usd, meta_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (event_type or "event")[:80],
                (source or "ia_dev")[:80],
                duration_ms,
                tokens_in,
                tokens_out,
                cost_usd,
                self._to_json(meta or {}),
                self._now(),
            ],
        )

    def get_observability_summary(self, *, window_seconds: int = 3600, limit: int = 2000) -> dict:
        self.ensure_tables()
        safe_window = max(60, min(int(window_seconds), 604800))
        safe_limit = max(10, min(int(limit), 5000))
        since = self._now() - safe_window
        rows = self._fetchall(
            """
            SELECT event_type, source, duration_ms, tokens_in, tokens_out, cost_usd, created_at
            FROM ia_dev_observability_events
            WHERE created_at >= %s
            ORDER BY id DESC
            LIMIT %s
            """,
            [since, safe_limit],
        )

        by_source: dict[str, dict] = defaultdict(
            lambda: {
                "events": 0,
                "durations_ms": [],
                "tokens_in": 0,
                "tokens_out": 0,
                "cost_usd": 0.0,
            }
        )
        by_event_type: dict[str, int] = defaultdict(int)

        total_events = 0
        total_tokens_in = 0
        total_tokens_out = 0
        total_cost_usd = 0.0
        all_durations: list[int] = []

        for row in rows:
            event_type = str(row[0] or "event")
            source = str(row[1] or "ia_dev")
            duration_ms = int(row[2]) if row[2] is not None else None
            tokens_in = int(row[3] or 0)
            tokens_out = int(row[4] or 0)
            cost_usd = float(row[5] or 0.0)

            total_events += 1
            total_tokens_in += tokens_in
            total_tokens_out += tokens_out
            total_cost_usd += cost_usd
            by_event_type[event_type] += 1

            bucket = by_source[source]
            bucket["events"] += 1
            bucket["tokens_in"] += tokens_in
            bucket["tokens_out"] += tokens_out
            bucket["cost_usd"] += cost_usd
            if duration_ms is not None:
                bucket["durations_ms"].append(duration_ms)
                all_durations.append(duration_ms)

        def _duration_stats(values: list[int]) -> dict:
            if not values:
                return {"count": 0, "avg_ms": 0, "p95_ms": 0, "max_ms": 0}
            ordered = sorted(values)
            p95_idx = min(len(ordered) - 1, int(len(ordered) * 0.95))
            return {
                "count": len(ordered),
                "avg_ms": int(sum(ordered) / len(ordered)),
                "p95_ms": int(ordered[p95_idx]),
                "max_ms": int(ordered[-1]),
            }

        sources: dict[str, dict] = {}
        for source, bucket in by_source.items():
            durations = list(bucket.pop("durations_ms", []))
            sources[source] = {
                **bucket,
                "cost_usd": round(float(bucket["cost_usd"]), 8),
                "latency": _duration_stats(durations),
            }

        return {
            "window_seconds": safe_window,
            "sample_size": total_events,
            "event_types": dict(by_event_type),
            "totals": {
                "events": total_events,
                "tokens_in": total_tokens_in,
                "tokens_out": total_tokens_out,
                "cost_usd": round(total_cost_usd, 8),
                "latency": _duration_stats(all_durations),
            },
            "sources": sources,
        }
