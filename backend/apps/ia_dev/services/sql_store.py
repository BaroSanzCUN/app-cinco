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
