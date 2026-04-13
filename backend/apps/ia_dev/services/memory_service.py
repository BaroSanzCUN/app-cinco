import os
import threading
import time
import uuid

from .redis_cache_service import RedisCacheService
from .sql_store import IADevSqlStore


class SessionMemoryStore:
    _lock = threading.Lock()
    _max_messages = max(100, int(os.getenv("IA_DEV_MAX_MESSAGES", "100")))
    _store = IADevSqlStore()
    _cache = RedisCacheService()

    @classmethod
    def _new_session_id(cls) -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _cache_key(session_id: str) -> str:
        return f"memory:{session_id}"

    @classmethod
    def _empty_payload(cls) -> dict:
        return {
            "messages": [],
            "context": {},
            "trim_events": 0,
            "updated_at": int(time.time()),
        }

    @classmethod
    def _load_payload(cls, session_id: str) -> dict:
        cache_key = cls._cache_key(session_id)
        payload = cls._cache.get_json(cache_key, default=None)
        if isinstance(payload, dict):
            payload.setdefault("messages", [])
            payload.setdefault("context", {})
            payload.setdefault("trim_events", 0)
            payload.setdefault("updated_at", int(time.time()))
            return payload

        row = cls._store.get_session_memory(session_id)
        if not row:
            return cls._empty_payload()

        payload = {
            "messages": row.get("messages") or [],
            "context": row.get("context") or {},
            "trim_events": int(row.get("trim_events") or 0),
            "updated_at": int(row.get("updated_at") or int(time.time())),
        }
        cls._cache.set_json(cache_key, payload)
        return payload

    @classmethod
    def _save_payload(cls, session_id: str, payload: dict):
        payload["updated_at"] = int(time.time())
        cls._store.upsert_session_memory(
            session_id=session_id,
            messages=list(payload.get("messages") or []),
            context=dict(payload.get("context") or {}),
            trim_events=int(payload.get("trim_events") or 0),
            updated_at=int(payload["updated_at"]),
        )
        cls._cache.set_json(cls._cache_key(session_id), payload)

    @classmethod
    def get_or_create(cls, session_id: str | None = None) -> tuple[str, dict]:
        with cls._lock:
            sid = (session_id or "").strip() or cls._new_session_id()
            payload = cls._load_payload(sid)
            cls._save_payload(sid, payload)
            return sid, payload

    @classmethod
    def append_turn(cls, session_id: str, user_text: str, assistant_text: str):
        with cls._lock:
            payload = cls._load_payload(session_id)
            messages = list(payload.get("messages") or [])
            messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": assistant_text})
            overflow = len(messages) - cls._max_messages
            if overflow > 0:
                messages = messages[overflow:]
                payload["trim_events"] = int(payload.get("trim_events") or 0) + 1
            payload["messages"] = messages
            cls._save_payload(session_id, payload)

    @classmethod
    def get_recent_messages(cls, session_id: str, limit: int = 8) -> list[dict]:
        with cls._lock:
            payload = cls._load_payload(session_id)
            safe_limit = max(1, min(int(limit), cls._max_messages))
            return [dict(m) for m in (payload.get("messages") or [])[-safe_limit:]]

    @classmethod
    def get_context(cls, session_id: str) -> dict:
        with cls._lock:
            payload = cls._load_payload(session_id)
            return dict(payload.get("context") or {})

    @classmethod
    def update_context(cls, session_id: str, updates: dict):
        with cls._lock:
            payload = cls._load_payload(session_id)
            context = dict(payload.get("context") or {})
            context.update(dict(updates or {}))
            payload["context"] = context
            cls._save_payload(session_id, payload)

    @classmethod
    def reset(cls, session_id: str):
        with cls._lock:
            payload = cls._empty_payload()
            cls._save_payload(session_id, payload)

    @classmethod
    def status(cls, session_id: str) -> dict:
        with cls._lock:
            payload = cls._load_payload(session_id)
            used = len(payload.get("messages") or [])
            ratio = used / cls._max_messages if cls._max_messages else 0
            trim_events = int(payload.get("trim_events") or 0)
            return {
                "used_messages": used,
                "capacity_messages": cls._max_messages,
                "usage_ratio": round(ratio, 3),
                "trim_events": trim_events,
                "saturated": trim_events > 0 or ratio >= 0.9,
                "backend": "db+redis" if cls._cache.is_available else "db",
                "redis_enabled": cls._cache.is_available,
            }
