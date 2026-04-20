import os
import time
import uuid
from typing import Callable

from .observability_service import ObservabilityService
from .sql_store import IADevSqlStore


class AsyncJobService:
    def __init__(self):
        self.store = IADevSqlStore()
        self.observability = ObservabilityService()
        self.mode = (os.getenv("IA_DEV_ASYNC_MODE", "sync") or "sync").strip().lower()

    @staticmethod
    def _now() -> int:
        return int(time.time())

    def enqueue(
        self,
        *,
        job_type: str,
        payload: dict,
        idempotency_key: str | None = None,
        run_after: int | None = None,
    ) -> dict:
        if idempotency_key:
            existing = self.store.get_async_job_by_idempotency(idempotency_key)
            if existing:
                return existing

        job_id = f"JOB-{uuid.uuid4().hex[:10].upper()}"
        self.store.insert_async_job(
            job_id=job_id,
            job_type=job_type,
            payload=payload,
            status="pending",
            idempotency_key=idempotency_key,
            run_after=int(run_after or self._now()),
        )
        return self.store.get_async_job(job_id) or {
            "job_id": job_id,
            "job_type": job_type,
            "status": "pending",
            "payload": payload,
            "result": None,
            "error": None,
            "idempotency_key": idempotency_key,
            "created_at": self._now(),
            "updated_at": self._now(),
            "run_after": int(run_after or self._now()),
        }

    def process_pending(
        self,
        *,
        limit: int = 20,
        handler_registry: dict[str, Callable[[dict], dict]] | None = None,
    ) -> list[dict]:
        handlers = handler_registry or {}
        processed: list[dict] = []
        jobs = self.store.claim_pending_async_jobs(limit=limit)
        for job in jobs:
            job_id = str(job["job_id"])
            handler = handlers.get(str(job["job_type"]))
            if not handler:
                self.store.update_async_job(
                    job_id=job_id,
                    status="failed",
                    result=None,
                    error=f"Handler no registrado para job_type={job['job_type']}",
                )
                processed.append(self.store.get_async_job(job_id) or job)
                continue
            started = time.perf_counter()
            try:
                result = handler(job.get("payload") or {})
                self.store.update_async_job(
                    job_id=job_id,
                    status="done",
                    result=result if isinstance(result, dict) else {"result": result},
                    error=None,
                )
                self.observability.record_event(
                    event_type="async_job_done",
                    source=str(job.get("job_type") or "job"),
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    meta={"job_id": job_id},
                )
            except Exception as exc:
                self.store.update_async_job(
                    job_id=job_id,
                    status="failed",
                    result=None,
                    error=str(exc),
                )
                self.observability.record_event(
                    event_type="async_job_failed",
                    source=str(job.get("job_type") or "job"),
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    meta={"job_id": job_id, "error": str(exc)},
                )
            processed.append(self.store.get_async_job(job_id) or job)
        return processed
